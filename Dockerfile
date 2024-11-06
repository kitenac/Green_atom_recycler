FROM python:3.12-alpine
WORKDIR /atom_eco

# coppy all files inside cur dir: /atom_eco | [NOTE] .dockerignore filters unnecessory files
COPY . .

# нужно для отрисовки графа БД:
RUN apk update
RUN apk add --no-cache graphviz
RUN apk add --no-cache xdg-utils

# создать venv и пакеты установить
RUN python3 -m venv myenv
RUN source myenv/bin/activate

# Install the dependencies | [Note] happens on build => no need to reinstall it on each run 
# [reducing size] --no-cache-dir: pip won`t store the downloaded packages in its cache directory - This means that every time you run the pip install command, it will fetch the packages from the internet rather than using any previously cached versions.

RUN apk add --no-cache postgresql-dev       # install PostgreSQL development package - need for psycopg2 from req.txt
RUN pip install --no-cache-dir -r ./req.txt

# настроим ENV аргументы
ARG PORT=8001
ARG POSTGRES_PASSWORD="root"
ARG POSTGRES_USER="root"

ENV PORT=${PORT}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ENV POSTGRES_USER=${POSTGRES_USER}

# exposing container from port given as arguemnt to container
EXPOSE $PORT

# заполнить таблицы с мок-данными и запустить приложение
RUN chmod +x ./start.sh 
ENTRYPOINT ["./start.sh"]