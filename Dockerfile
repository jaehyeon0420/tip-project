FROM mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest

# Install MeCab system dependencies
RUN apt-get update && \
    # 1. Java 설치 시 충돌을 일으키는 누락된 디렉토리들을 미리 강제 생성
    mkdir -p /usr/share/man/man1 /usr/share/man/man2 /usr/share/man/man7 /usr/share/man/man8 && \
    # 2. 대화형 설정창 무시 및 의존성 꼬임 방지를 위한 환경 변수 설정
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openjdk-11-jdk-headless \
    ca-certificates-java && \
    # 3. MeCab 및 기타 도구 설치
    apt-get install -y \
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
    autoconf && \
    # 4. (중요) 설치 후 Java 인증서 설정 강제 업데이트
    update-ca-certificates -f && \
    # 5. 캐시 정리
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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

# Download NLTK data for g2pk
RUN python -m nltk.downloader cmudict
