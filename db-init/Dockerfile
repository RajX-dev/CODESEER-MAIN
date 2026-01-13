FROM postgres:15

COPY schema.sql /schema.sql

CMD ["psql", "-h", "codeseer-postgres", "-U", "codeseer", "-d", "codeseer", "-f", "/schema.sql"]
