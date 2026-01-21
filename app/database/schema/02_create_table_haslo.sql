CREATE TYPE typ_hasla AS ENUM('student', 'starosta');

CREATE TABLE IF NOT EXISTS haslo (
    kod VARCHAR(50) PRIMARY KEY,
    typ typ_hasla NOT NULL,
    email VARCHAR(50) NOT NULL,
    data_waznosci TIMESTAMP
);