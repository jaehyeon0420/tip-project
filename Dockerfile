FROM mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest

# Install MeCab system dependencies
RUN apt-get update && apt-get install -y \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    git \
    make \
    curl \
    xz-utils \
    file \
    sudo \
    automake \
    libtool \
    autoconf \
    && rm -rf /var/lib/apt/lists/*

# Install mecab-ko
WORKDIR /tmp
RUN curl -LO https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz \
    && tar zxfv mecab-0.996-ko-0.9.2.tar.gz \
    && cd mecab-0.996-ko-0.9.2 \
    && ./configure \
    && make \
    && make check \
    && make install \
    && ldconfig

# Install mecab-ko-dic
RUN curl -LO https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz \
    && tar -zxvf mecab-ko-dic-2.1.1-20180720.tar.gz \
    && cd mecab-ko-dic-2.1.1-20180720 \
    && ./autogen.sh \
    && ./configure \
    && make \
    && make install

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install azureml-core for environment variables support
RUN pip install --no-cache-dir azureml-core
