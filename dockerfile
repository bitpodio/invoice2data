FROM tesseractshadow/tesseract4re:latest

RUN apt-get update && \
    apt-get install -y tzdata &&\
    apt-get install -y python-pip

RUN apt-get install -y git 

RUN apt-get install -y python3-setuptools && apt-get install -y python3-dev

RUN apt-get install -y imagemagick

RUN cd /tmp && ls && git clone https://github.com/bitpodio/invoice2data.git && cd ./invoice2data && python3 setup.py install

#Setting the timezone
ENV TZ=America/New_York