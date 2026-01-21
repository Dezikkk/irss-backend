CREATE TABLE IF NOT EXISTS studia (
    id SERIAL PRIMARY KEY,
    token VARCHAR(50) NOT NULL UNIQUE,
    email_starosty VARCHAR(50) NOT NULL,
    opis TEXT,
    ilosc_grup INT NOT NULL,
    maks_osob INT[] NOT NULL,
    data_utworzenia TIMESTAMP NOT NULL DEFAULT NOW(),
    data_zakonczenia TIMESTAMP NOT NULL
);
