FROM ubuntu:bionic

MAINTAINER IIIT <github@iiit.pl>

ADD requirements.txt /requirements.txt

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    TZ=Europe/Warsaw \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

ENV PACKAGES="\
    apache2-utils \
    binutils \
    curl \
    gdal-bin \
    gettext \
    git \
    libproj-dev \
    locales \
    nginx \
    python3 \
    python3-dev \
    python3-pip \
    syslinux \
    tar \
    tzdata \
    unzip \
    wget \
    "

ENV DEV_PACKAGES="\
    libcurl4-openssl-dev \
    libssl-dev \
    "

ADD docker/config/uwsgi.ini /uwsgi.ini
ADD docker/scripts /scripts

RUN echo $TZ > /etc/timezone && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    apt-get update && \
    apt-get install -y -f $PACKAGES $DEV_PACKAGES && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    echo "LC_ALL=$LC_ALL" >> /etc/environment && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "LANG=$LANG" > /etc/locale.conf && \
    locale-gen $LANG && \
    pip install -r /requirements.txt && \
    rm -rf /root/.cache/ && \
    rm -rf /usr/src/ && \
    mkdir /run/nginx/ && \
    mkdir /celerybeat && \
    apt-get remove $DEV_PACKAGES -y && \
    apt-get autoremove -y

ADD docker/config/nginx.conf /etc/nginx/nginx.conf
ADD docker/config/nginx /etc/nginx/sites-available/

ADD src /release-manager

WORKDIR /release-manager

VOLUME /release-manager

COPY docker/scripts/docker-entrypoint /docker-entrypoint

ENTRYPOINT ["/docker-entrypoint"]
