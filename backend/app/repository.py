import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing

from .domain import Classification, Estado, Reading, StoredReading


class ReadingRepository(ABC):
    @abstractmethod
    def add(self, reading: Reading, classification: Classification, criado_em: str) -> StoredReading: ...

    @abstractmethod
    def latest(self, limit: int) -> list: ...


class SqliteReadingRepository(ReadingRepository):
    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperatura REAL NOT NULL,
            umidade REAL NOT NULL,
            luminosidade REAL NOT NULL,
            ligada INTEGER NOT NULL,
            estado TEXT NOT NULL,
            condicoes TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """

    def __init__(self, path: str):
        self._path = path
        with closing(self._connect()) as conn, conn:
            conn.execute(self._SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def add(self, reading, classification, criado_em):
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO readings "
                "(temperatura, umidade, luminosidade, ligada, estado, condicoes, criado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    reading.temperatura,
                    reading.umidade,
                    reading.luminosidade,
                    int(reading.ligada),
                    classification.estado.value,
                    ",".join(classification.condicoes),
                    criado_em,
                ),
            )
            new_id = cursor.lastrowid
        return StoredReading(
            id=new_id,
            temperatura=reading.temperatura,
            umidade=reading.umidade,
            luminosidade=reading.luminosidade,
            ligada=reading.ligada,
            estado=classification.estado,
            condicoes=classification.condicoes,
            criado_em=criado_em,
        )

    def latest(self, limit):
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, temperatura, umidade, luminosidade, ligada, estado, condicoes, criado_em "
                "FROM readings ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            StoredReading(
                id=r[0],
                temperatura=r[1],
                umidade=r[2],
                luminosidade=r[3],
                ligada=bool(r[4]),
                estado=Estado(r[5]),
                condicoes=tuple(r[6].split(",")) if r[6] else (),
                criado_em=r[7],
            )
            for r in rows
        ]


class PostgresReadingRepository(ReadingRepository):
    """Mesmo contrato do SQLite, para o banco gerenciado da Azure (PostgreSQL).

    `connect` recebe a URL e devolve uma conexão no estilo psycopg 3. Por padrão
    usa o psycopg; os testes podem injetar outra função.
    """

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS readings (
            id BIGSERIAL PRIMARY KEY,
            temperatura DOUBLE PRECISION NOT NULL,
            umidade DOUBLE PRECISION NOT NULL,
            luminosidade DOUBLE PRECISION NOT NULL,
            ligada BOOLEAN NOT NULL,
            estado TEXT NOT NULL,
            condicoes TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """

    def __init__(self, url: str, connect=None):
        if connect is None:
            import psycopg  # só é necessário quando o PostgreSQL é usado
            connect = psycopg.connect
        self._url = url
        self._connect_fn = connect
        with self._connect() as conn:
            conn.execute(self._SCHEMA)

    def _connect(self):
        return self._connect_fn(self._url)

    def add(self, reading, classification, criado_em):
        with self._connect() as conn:
            new_id = conn.execute(
                "INSERT INTO readings "
                "(temperatura, umidade, luminosidade, ligada, estado, condicoes, criado_em) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    reading.temperatura,
                    reading.umidade,
                    reading.luminosidade,
                    bool(reading.ligada),
                    classification.estado.value,
                    ",".join(classification.condicoes),
                    criado_em,
                ),
            ).fetchone()[0]
        return StoredReading(
            id=new_id,
            temperatura=reading.temperatura,
            umidade=reading.umidade,
            luminosidade=reading.luminosidade,
            ligada=reading.ligada,
            estado=classification.estado,
            condicoes=classification.condicoes,
            criado_em=criado_em,
        )

    def latest(self, limit):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, temperatura, umidade, luminosidade, ligada, estado, condicoes, criado_em "
                "FROM readings ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [
            StoredReading(
                id=r[0],
                temperatura=r[1],
                umidade=r[2],
                luminosidade=r[3],
                ligada=bool(r[4]),
                estado=Estado(r[5]),
                condicoes=tuple(r[6].split(",")) if r[6] else (),
                criado_em=r[7],
            )
            for r in rows
        ]
