-- Use environment variables to avoid hardcoding database credentials
CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE}
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
CREATE USER '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE}.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
