FROM ubuntu:20.04

# disclaimer: probably doesn't follow Docker best practices
# the objective here is one image with all the components for a data pipeline in a box
# - Anaconda python distribution
# - DuckDB 'data warehouse'
# - dagster orchestrator
# - Meltano CLI for Singer taps and Airbyte connectors
# - Great Expectations data quality
# - Superset data visualization / dashboards
# separate containers can be launched from this image to run different parts of the pipeline interactively
# or build on this dockerfile with modifications to launch components via CMD

# Install dependencies

RUN apt-get update && apt-get upgrade -y && \
  # set timezone, needed for non-interactive install
  ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
  dpkg-reconfigure --frontend noninteractive tzdata && \
  apt-get install -y build-essential \
  openssh-server \
  git-all \
  rsync \
  postgresql-client \
  curl \
  sudo \
  wget \
  libssl-dev \
  libffi-dev \
  libsasl2-dev \
  libldap2-dev \
  default-libmysqlclient-dev
  
# Add user ubuntu with no password, add to sudo group
RUN adduser --disabled-password --gecos '' ubuntu && \
  adduser ubuntu sudo && \
  echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# set up sshd
# https://docs.docker.com/engine/examples/running_ssh_service/
# enables running e.g. VS Code with ssh to remote

RUN mkdir /var/run/sshd && \
  echo 'ubuntu:ubuntu' | chpasswd && \
  echo 'root:freelunch' | chpasswd && \
  sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
# SSH login fix. Otherwise user is kicked off after login
  sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

USER ubuntu
WORKDIR /home/ubuntu/

# install Anaconda
# https://www.anaconda.com/distribution/#download-section

ARG CONDA_VERSION=2022.10
ARG PYTHON_VERSION=3.9

RUN wget https://repo.anaconda.com/archive/Anaconda3-${CONDA_VERSION}-Linux-x86_64.sh
RUN bash Anaconda3-${CONDA_VERSION}-Linux-x86_64.sh -b && \
  rm Anaconda3-${CONDA_VERSION}-Linux-x86_64.sh
  
ENV PATH /home/ubuntu/anaconda3/bin:$PATH

RUN conda init && \
  conda update conda && \
  conda install -c anaconda ipykernel

# install a certificate and configure SSL
# openssl req -x509 -nodes -days 365 -newkey rsa:1024 -keyout mycert.pem -out mycert.pem
# <hit enter for everything>
RUN mkdir -p '/home/ubuntu/certs'
COPY mycert.pem /home/ubuntu/certs/mycert.pem
RUN sudo chown ubuntu:ubuntu /home/ubuntu/certs/mycert.pem

EXPOSE 8888
EXPOSE 22

RUN conda create --name mds python=${PYTHON_VERSION}
# https://pythonspeed.com/articles/activate-conda-dockerfile/
SHELL ["conda", "run", "-n", "mds", "/bin/bash", "-c"]
RUN conda update --all

# Install DuckDB, dbt etc.
RUN pip install duckdb duckdb-engine ipython-sql sqlalchemy seaborn ipykernel dbt-core dbt-postgres dbt-duckdb dagster dagit
RUN mkdir -p '/home/ubuntu/.dbt'
COPY profiles.yml /home/ubuntu/.dbt/profiles.yml

# add this conda environment to Jupyter
RUN python -m ipykernel install --user --name=mds

# Install Airflow - skipped in favor of dagster
# ARG AIRFLOW_VERSION=2.4.3

# RUN pip install apache-airflow
# RUN pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-no-providers-${PYTHON_VERSION}.txt"
# RUN airflow db init
# RUN airflow users create \
#     --username admin \
#     --password admin \
#     --firstname Airflow \
#     --lastname Admin \
#     --role Admin \
#     --email myuser@mydomain12345.com
# RUN airflow webserver -D
# RUN airflow scheduler -D
# EXPOSE 8080

# Install Meltano
RUN pip install meltano

# Install Great Expectations in new env due to some conflicts
RUN conda create --name great_expectations python=${PYTHON_VERSION}
SHELL ["conda", "run", "-n", "great_expectations", "/bin/bash", "-c"]
RUN conda update --all
RUN pip install great_expectations ipykernel
# add this conda environment to Jupyter
RUN python -m ipykernel install --user --name=great_expectations

# Install Superset in new env
RUN conda create --name superset python=3.8
SHELL ["conda", "run", "-n", "superset", "/bin/bash", "-c"]
RUN conda update --all
RUN pip install --upgrade pip
RUN pip install --force-reinstall cryptography==38.0.4
RUN pip install --force-reinstall wtforms==2.3.3
RUN pip install Pillow apache-superset ipykernel
# add this conda environment to Jupyter
RUN python -m ipykernel install --user --name=superset

ENV FLASK_APP superset
RUN echo Superset\nAdmin\nmyuser@mydomain123456.com\nadmin\nadmin\n | superset db upgrade
RUN superset init
EXPOSE 8088

# Configure access to Jupyter with password 'emergent'

RUN mkdir -p '/home/ubuntu/.jupyter'
COPY jupyter_notebook_config.py /home/ubuntu/.jupyter/jupyter_notebook_config.py

COPY runservices.sh /home/ubuntu/runservices.sh
RUN sudo chown ubuntu:ubuntu /home/ubuntu/runservices.sh && chmod +x /home/ubuntu/runservices.sh
CMD ["bash"]
# CMD ["/home/ubuntu/runservices.sh"]

# docker run -ti -p 28888:8888 -p 2222:22 -p 8080:8080 -v ~/notebooks/MTA:/mnt --rm mds /bin/bash

# install docker - https://docs.docker.com/get-docker/
# docker build -t mds .
# run image in container, mount directory where you cloned the repo
# docker run -ti -p 28888:8888 -p 2222:22 -p 8088:8088 -v ~/projects/MTA:/mnt --rm mds /bin/bash
# cd /mnt
# conda active mds
# ./build-docker.sh
# conda active superset
# superset run -p 8088 --with-threads --reload --debugger

