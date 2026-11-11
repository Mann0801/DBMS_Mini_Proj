-- CampusEats: one-time setup. Run as the database root user:
--   sudo mariadb < database/setup.sql
-- Change the password here AND in your .env file.

CREATE DATABASE IF NOT EXISTS campuseats
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'campuseats'@'localhost' IDENTIFIED BY 'change_me';
-- also (re)set the password in case the user already existed
ALTER USER 'campuseats'@'localhost' IDENTIFIED BY 'change_me';

-- ALL on this one database covers tables, triggers, procedures and views.
GRANT ALL PRIVILEGES ON campuseats.* TO 'campuseats'@'localhost';

FLUSH PRIVILEGES;
