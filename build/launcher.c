/* Cross-platform bootstrapper — launches bin/<same-name> with all arguments.
 *
 * The outer exe lives at the project root (e.g. pyscripts).
 * The inner exe is the Nuitka-compiled program under bin/.
 *
 * Compile:
 *   Windows (MSVC):   cl /O2 /Fe:PyScripts.exe /source-charset:utf-8 launcher.c
 *   Windows (MinGW):  gcc -O2 -o pyscripts.exe launcher.c -lshlwapi -mwindows
 *   Windows (Clang):  clang -O2 -o pyscripts.exe launcher.c -lshlwapi -mwindows
 *   Linux/macOS:      cc -O2 -o pyscripts launcher.c
 *   macOS (old SDK):  cc -O2 -o pyscripts launcher.c -framework CoreFoundation
 *
 * Note: WinMain entry point is used on Windows so no console window appears.
 *       MinGW/Clang need -mwindows; MSVC infers it automatically from WinMain.
 */

/* ========================================================================
 * Windows implementation
 * ======================================================================== */
#if defined(_WIN32)

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlwapi.h>
#include <shellapi.h>
#include <stdio.h>

#ifdef _MSC_VER
#  pragma comment(lib, "shlwapi.lib")
#  pragma comment(lib, "shell32.lib")
#  pragma comment(lib, "user32.lib")
#endif

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                   LPSTR lpCmdLine, int nCmdShow) {
    wchar_t self[MAX_PATH];
    wchar_t inner[MAX_PATH + 8];
    wchar_t *name;

    (void)hInstance; (void)hPrevInstance; (void)lpCmdLine; (void)nCmdShow;

    /* Full path of this executable */
    if (GetModuleFileNameW(NULL, self, MAX_PATH) == 0) return 1;

    /* Strip to directory (keep trailing backslash) */
    name = wcsrchr(self, L'\\');
    if (!name) return 1;
    wchar_t fname[MAX_PATH];
    wcscpy_s(fname, MAX_PATH, name + 1); /* copy before truncation */
    self[name - self + 1] = L'\0';

    /* Build path: <self_dir>bin\<same_name> */
    wcscpy_s(inner, MAX_PATH + 8, self);
    wcscat_s(inner, MAX_PATH + 8, L"bin\\");
    wcscat_s(inner, MAX_PATH + 8, fname);

    if (!PathFileExistsW(inner)) return 1;

    /* Parse original command line to retrieve args (excluding our launcher path) */
    int argc;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) return 1;

    /* Build command line: "inner" "arg1" "arg2" ... */
    wchar_t cmdline[32768];
    wchar_t *p = cmdline;
    size_t rem = sizeof(cmdline) / sizeof(wchar_t) - 1;

    p += swprintf_s(p, rem, L"\"%s\"", inner);
    rem = sizeof(cmdline) / sizeof(wchar_t) - (p - cmdline) - 1;

    for (int i = 1; i < argc && rem > 2; i++) {
        int r = swprintf_s(p, rem, L" \"%s\"", argv[i]);
        if (r > 0) { p += r; rem -= r; }
    }

    LocalFree(argv);

    STARTUPINFOW si  = {sizeof(si)};
    PROCESS_INFORMATION pi;

    if (!CreateProcessW(NULL, cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        return 1;

    WaitForSingleObject(pi.hProcess, INFINITE);

    DWORD ec;
    GetExitCodeProcess(pi.hProcess, &ec);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)ec;
}

/* ========================================================================
 * POSIX implementation (Linux, macOS, *BSD, Solaris …)
 * ======================================================================== */
#else

#define _POSIX_C_SOURCE 200809L
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <libgen.h>
#include <limits.h>

#if defined(__APPLE__)
#  include <mach-o/dyld.h>
#elif defined(__FreeBSD__)
#  include <sys/sysctl.h>
#  include <sys/types.h>
#endif

/* Resolve the absolute path of this executable into buf (size >= PATH_MAX). */
static int self_path(char *buf, size_t size) {
#if defined(__linux__)
    ssize_t len = readlink("/proc/self/exe", buf, size - 1);
    if (len > 0) { buf[len] = '\0'; return 0; }
#elif defined(__APPLE__)
    uint32_t len = (uint32_t)size;
    if (_NSGetExecutablePath(buf, &len) == 0) {
        char *resolved = realpath(buf, NULL);
        if (resolved) {
            (void)strncpy(buf, resolved, size - 1);
            buf[size - 1] = '\0';
            free(resolved);
        }
        return 0;
    }
#elif defined(__FreeBSD__)
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PATHNAME, -1};
    size_t len = size;
    if (sysctl(mib, 4, buf, &len, NULL, 0) == 0) return 0;
#elif defined(__sun)
    char *p = getexecname();
    if (p) {
        (void)strncpy(buf, p, size - 1);
        buf[size - 1] = '\0';
        return 0;
    }
#endif
    return -1;
}

int main(int argc, char *argv[]) {
    char self[PATH_MAX];
    char inner[PATH_MAX];
    char *name;

    if (self_path(self, sizeof(self)) != 0) return 1;

    /* Strip filename, keep trailing slash */
    name = strrchr(self, '/');
    if (!name) return 1;
    char fname[PATH_MAX];
    (void)strncpy(fname, name + 1, sizeof(fname) - 1);
    fname[sizeof(fname) - 1] = '\0';
    name[1] = '\0';

    /* Build path: <self_dir>bin/<same_name> */
    (void)snprintf(inner, sizeof(inner), "%sbin/%s", self, fname);

    if (access(inner, X_OK) != 0) return 1;

    /* Build argv: inner_path, original argv[1..], NULL */
    char **child_argv = malloc((size_t)(argc + 1) * sizeof(char *));
    if (!child_argv) return 1;
    child_argv[0] = inner;
    for (int i = 1; i < argc; i++) child_argv[i] = argv[i];
    child_argv[argc] = NULL;

    pid_t pid = fork();
    if (pid == -1) { free(child_argv); return 1; }

    if (pid == 0) {
        /* Child — replace with inner binary */
        execv(inner, child_argv);
        _exit(127);  /* only reached on error */
    }

    free(child_argv);

    /* Parent — wait for child */
    int status;
    waitpid(pid, &status, 0);

    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 1;
}

#endif /* _WIN32 */
