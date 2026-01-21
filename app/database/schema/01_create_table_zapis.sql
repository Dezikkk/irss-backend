CREATE TABLE IF NOT EXISTS zapis (
    id SERIAL PRIMARY KEY,
    studia_id INT NOT NULL REFERENCES studia(id),
    email VARCHAR(50) NOT NULL UNIQUE,
    priorytety INT[] NOT NULL,
    data_utworzenia TIMESTAMP NOT NULL DEFAULT NOW()
);
