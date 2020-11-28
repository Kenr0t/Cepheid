FROM tiangolo/uwsgi-nginx-flask:python3.8

# copy over our requirements.txt file
COPY ./requirements.txt /tmp/

# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt

# copy over our app code
RUN apt-get update
RUN apt-get --no-install-recommends install -y ca-certificates
RUN git clone https://github.com/Kenr0t/Cepheid.git
RUN cd Cepheid
COPY ./app /app

EXPOSE 4013
ENV LISTEN_PORT 4013
