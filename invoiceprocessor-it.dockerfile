FROM tesseractshadow/tesseract4re:latest

WORKDIR /home/app/

RUN apt-get update && \
    apt-get install -y tzdata &&\
    apt-get install -y python-pip &&\
    apt-get install -y python3-setuptools &&\
    apt-get install -y python3-dev &&\
    apt-get install -y imagemagick &&\
    apt-get clean

#RUN git clone https://github.com/bitpodio/invoice2data.git -b job_creation --single-branch && cd ./invoice2data && python3 setup.py install
COPY ./ /home/app/

RUN python3 setup.py install &&\
    rm -rf /home/app/*

ENV TZ=America/New_York

ENTRYPOINT [ "invoice2data"]