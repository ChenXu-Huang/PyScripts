mkdir -p dist/package
mv dist/main.dist dist/package/bin
mv dist/pyscripts* dist/package/
cp -r assets dist/package/assets
cp -r lang  dist/package/lang
rm -rf dist/main.build
