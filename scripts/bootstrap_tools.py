"""Download the project-local Java/Tomcat/Maven tools if they are absent."""
import concurrent.futures
import pathlib
import urllib.request
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
tools = root / '.tools'
tools.mkdir(exist_ok=True)
items = [
 ('jdk-21.0.8+9', 'https://aka.ms/download-jdk/microsoft-jdk-21.0.8-windows-x64.zip'),
 ('apache-tomcat-10.1.44', 'https://archive.apache.org/dist/tomcat/tomcat-10/v10.1.44/bin/apache-tomcat-10.1.44.zip'),
 ('apache-maven-3.9.11', 'https://archive.apache.org/dist/maven/maven-3/3.9.11/binaries/apache-maven-3.9.11-bin.zip'),
]
def download(item):
 name, url = item
 if (tools / name).exists():
  return
 archive = tools / (name + '.zip')
 print('Downloading', name, flush=True)
 urllib.request.urlretrieve(url, archive)
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if not (tools / info.filename).resolve().is_relative_to(tools.resolve()):
    raise ValueError('Unsafe archive path')
  z.extractall(tools)
 print('Ready:', name, flush=True)
with concurrent.futures.ThreadPoolExecutor(3) as pool:
 list(pool.map(download, items))
