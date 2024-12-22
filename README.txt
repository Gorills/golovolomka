        
Django установленный системой автоматической установки cms LTD BEGET

=> Действия описанные ниже необходимо выполнять в docker-окружении выполнив команду ниже <=
$ ssh localhost -p222

для установки дополнительных модулей используйте pip
сам Django располагается в папке /home/s/shopds7k/shopds7k.beget.tech/public_html/venv/

для начала надо переключиться на текущий virtualenv
заходим в папку с проектом

$ cd /home/s/shopds7k/shopds7k.beget.tech/public_html
$ source venv/bin/activate

проверяем правильно ли определился путь до pip:
$ which pip
/home/s/shopds7k/shopds7k.beget.tech/public_html/venv/bin/pip

теперь мы можем пользоваться pip'ом для установки модулей не указывая полного пути до исполняемого файла:

$ pip install <Module-name>

где <Module-name> имя модуля который мы хотим установить

Для перезапуска passenger в папке проекта достаточно выполнить команду touch на пустом файле restart.txt

$ pwd
touch /home/s/shopds7k/shopds7k.beget.tech/public_html/main/main/tmp/restart.txt
$ touch restart.txt