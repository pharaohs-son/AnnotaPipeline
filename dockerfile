

FROM ubuntu:20.04
ENV DEBIAN_FRONTEND="noninteractive"

# --------------------------------
# envs
ENV IPR="5"
ENV HMMER_VERSION="3.4"
ENV IPRSCAN_VERSION="5.68-100.0"
ENV BLAST_VERSION="2.16.0"
ENV PERCOLATOR_VERSION="3-07-01"
ENV COMMET_VERSION="2021010"
ENV TZ=Europe/London
ENV XERCES_VERSION="3.2.4"

# --------------------------------
RUN apt-get update -y 

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update -y && \
    apt-get install -y wget python3.8 python2.7 openjdk-11-jre-headless libpcre2-dev libgomp1 perl-doc && \
    ln -s /usr/bin/python3.8 /usr/bin/python3 && ln -s /usr/bin/python3.8 /usr/bin/python

RUN apt-get install -y software-properties-common build-essential wget git autoconf libgsl-dev \ 
    libboost-all-dev libsuitesparse-dev liblpsolve55-dev libsqlite3-dev libmysql++-dev g++ xsdcxx \ 
    libboost-iostreams-dev zlib1g-dev libbamtools-dev samtools libhts-dev libboost-all-dev cdbfasta  \
    diamond-aligner libfile-which-perl libparallel-forkmanager-perl libyaml-perl libdbd-mysql-perl \
    curl cmake zip unzip  ca-certificates libboost-dev  libboost-filesystem-dev  libboost-system-dev libboost-thread-dev \
    libtokyocabinet-dev zlib1g-dev libbz2-dev rpm python3-distutils 
RUN apt-get install -y --no-install-recommends python3-biopython
# percolator req
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test && \
    apt install -y g++-11

# --------------------------------
# Install Blast
RUN mkdir /opt/blast
WORKDIR /opt/blast
RUN wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz  && \
    tar zxf ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz --strip-components=1
RUN rm -f ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz 
ENV PATH="$PATH:/opt/blast/bin"
# --------------------------------
# Download Interproscan
RUN curl -o /opt/interproscan-${IPRSCAN_VERSION}.tar.gz ftp://ftp.ebi.ac.uk/pub/software/unix/iprscan/${IPR}/${IPRSCAN_VERSION}/alt/interproscan-core-${IPRSCAN_VERSION}.tar.gz

WORKDIR /opt/
# --------------------------------
# Install InterProScan5.
RUN mkdir -p /opt/interproscan
# no db
RUN  tar -pxvzf interproscan-${IPRSCAN_VERSION}.tar.gz \
    -C /opt/interproscan --strip-components=1

RUN rm -f /opt/interproscan-${IPRSCAN_VERSION}-64-bit.tar.gz
ENV PATH="/opt/interproscan/bin:/opt/interproscan/:$PATH"
# --------------------------------
# Install hmmer
RUN mkdir /opt/hmmer
WORKDIR /opt/hmmer
RUN wget http://eddylab.org/software/hmmer/hmmer-${HMMER_VERSION}.tar.gz && \
    tar zxf hmmer-${HMMER_VERSION}.tar.gz --strip-components=1 && \
    ./configure --prefix /opt/hmmer  && \
    make  && \
    make check  && \
    make install

RUN rm -f hmmer-${HMMER_VERSION}.tar.gz
ENV PATH="/opt/hmmer/bin:$PATH"
# --------------------------------
# Install Augustus
WORKDIR /opt/
RUN git clone https://github.com/Gaius-Augustus/Augustus.git  && \
    cd Augustus  && \
    make augustus

ENV PATH="/opt/Augustus/bin:/opt/Augustus/scripts:$PATH" 
ENV AUGUSTUS_CONFIG_PATH="/opt/Augustus/config/"

## Install kallisto
WORKDIR /opt/
RUN git clone https://github.com/pachterlab/kallisto.git && \
    cd kallisto && \
    mkdir build && \
    cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX:PATH=/opt/kallisto && \
    make

RUN ln -s /opt/kallisto/build/src/kallisto /bin/kallisto
## Install comet
RUN mkdir /opt/comet
WORKDIR  /opt/comet
RUN wget https://sourceforge.net/projects/comet-ms/files/comet_${COMMET_VERSION}.zip && \
    unzip comet_${COMMET_VERSION}.zip && \
    mv comet.${COMMET_VERSION}.debian.exe comet && \
    chmod 777 comet

RUN rm -f comet.${COMMET_VERSION}.win64.exe comet.${COMMET_VERSION}.win32.exe comet.${COMMET_VERSION}.linux.exe comet.${COMMET_VERSION}.zip comet_source.${COMMET_VERSION}.zip 
RUN ln -s /opt/comet/comet /bin/comet


## Install percolator req
RUN mkdir /opt/percolator && \
    mkdir /opt/percolator/xerces && \
    cd /opt/percolator/xerces

RUN wget --no-check-certificate https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-${XERCES_VERSION}.tar.gz && \
    tar xzf xerces-c-${XERCES_VERSION}.tar.gz --strip-components=1 

RUN ./configure --prefix=/opt/percolator/xerces --disable-netaccessor-curl --disable-transcoder-icu > xercesc_config.log 2>&1
RUN make > xercesc_make.log 2>&1
RUN make install > xercesc_install.log 2>&1
RUN rm -f xerces-c-${XERCES_VERSION}.tar.gz


## Install percolator
WORKDIR  /opt/percolator
RUN wget https://github.com/percolator/percolator/archive/refs/tags/rel-${PERCOLATOR_VERSION}.tar.gz && \
    tar -xf rel-${PERCOLATOR_VERSION}.tar.gz --strip-components=1 && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make

RUN ln -s /opt/percolator/build/src/percolator /bin/percolator

RUN rm -f rel-${PERCOLATOR_VERSION}.tar.gz

WORKDIR /
## Install AnnotaPipeline
# --------------------------------
RUN git clone https://github.com/pharaohs-son/AnnotaPipeline && \
    cd AnnotaPipeline && \
    pip install .

WORKDIR /home