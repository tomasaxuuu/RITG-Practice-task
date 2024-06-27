import paramiko
import stat
import re
from bs4 import BeautifulSoup

# Настройки подключения
hostname = '46.4.244.188'
username = 'root'
key_filename = 'C:/Users/messi/.ssh/keitarosup/key.pub'  # Путь к ключу в формате PuTTY PPK
remote_dir = '/var/www/keitaro/s'  # Удалённая директория, в которой находится index.php
passphrase = 'Du*vcs_!TeMytZ!Ax38sUXXhFJFNT4Lp'  # Пароль для расшифровки зашифрованного ключа

# Ожидаемые PHP функции
expected_php_functions = [
    'getImgPath',
    'getPeoplesCountry',
    'getPeopleCountry',
    'getNameLanding',
    'getNameCountry'
]

# Загрузка зашифрованного ключа
key = paramiko.RSAKey.from_private_key_file(key_filename, password=passphrase)

# Подключение к серверу
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(hostname=hostname, username=username, pkey=key)
    print("Успешное подключение к серверу")

    # Создание SFTP-сессии
    sftp = ssh.open_sftp()

    # Функция для рекурсивного поиска файлов с расширением .js
    def find_js_files(dir_path):
        js_files = []
        for item in sftp.listdir_attr(dir_path):
            item_path = f"{dir_path}/{item.filename}"
            if item.filename.endswith('.js'):
                js_files.append(item_path)
            elif stat.S_ISDIR(item.st_mode):
                js_files.extend(find_js_files(item_path))
        return js_files

    # Функция для получения содержимого файла на удалённом сервере
    def get_file_content(file_path):
        with sftp.file(file_path, 'r') as file:
            return file.read().decode('utf-8')

    # Запрос названия подкаталога
    sub_dir = input("Введите название подкаталога в директории s/: ")
    full_path = f"{remote_dir}/{sub_dir}"

    # Перейти в подкаталог
    sftp.chdir(full_path)
    print(f"Перешли в подкаталог {full_path}")

    # Поиск файлов с расширением .js
    js_files = find_js_files(full_path)
    if js_files:
        print("Найденные .js файлы:")
        for js_file in js_files:
            print(js_file)
    else:
        print("Файлы с расширением .js не найдены.")

    # Проверка наличия CDN jQuery в index.php
    index_php_path = f"{full_path}/index.php"
    with sftp.file(index_php_path, 'r') as file:
        # Декодируем байтовый объект в строку
        php_content = file.read().decode('utf-8')

        # Используем BeautifulSoup для парсинга HTML/PHP
        soup = BeautifulSoup(php_content, 'html.parser')

        # Находим все теги <script> с атрибутом src
        script_tags = soup.find_all('script')

        # Извлекаем имена файлов .js из полных путей
        js_filenames = [js_file.split('/')[-1] for js_file in js_files]

        # Список для хранения ненайденных .js файлов
        missing_js_files = []

        for script_tag in script_tags:
            src = script_tag.get('src', '')
            if src:
                filename = src.split('/')[-1]
                if filename in js_filenames:
                    js_filenames.remove(filename)

        if js_filenames:
            print("Следующие .js файлы не найдены в index.php:")
            for js_filename in js_filenames:
                for js_file in js_files:
                    if js_file.endswith(js_filename):
                        print(js_file)
        else:
            print("Все .js файлы найдены в index.php")

        # Находим все текстовые участки между <?php и ?>
        php_tags = re.findall(r'(?<=<\?php).*?(?=\?>)', php_content, re.DOTALL)

        # Выводим найденные названия функций PHP
        found_php_functions = []

        for php_tag in php_tags:
            # Удаление лишних пробелов и переносов строк из текста между <?php и ?>
            php_function = php_tag.strip()
            if php_function:
                found_php_functions.append(php_function.split('(')[0].strip())  # Получаем имя функции

        if found_php_functions:
            print("Найденные PHP-функции в index.php:")
            for func in found_php_functions:
                print(f"{func}();")
        else:
            print("PHP-функции не найдены в index.php")

        # Проверяем наличие всех ожидаемых PHP функций
        missing_php_functions = [func for func in expected_php_functions if func not in found_php_functions]

        if missing_php_functions:
            print("Следующие PHP-функции не найдены в index.php:")
            for func in missing_php_functions:
                print(f"{func}();")
        else:
            print("Все ожидаемые PHP-функции найдены в index.php")

    # Закрытие SFTP-сессии
    sftp.close()

except paramiko.AuthenticationException as e:
    print(f"Ошибка аутентификации: {e}")
except paramiko.SSHException as e:
    print(f"Ошибка SSH: {e}")
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    ssh.close()