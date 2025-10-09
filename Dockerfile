# syntax=docker/dockerfile:1

# cannot do 24.04 because of freesurfer (libc6 << 2.36)
FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu22.04


# # modified from fmriprep (https://github.com/nipreps/fmriprep/blob/master/Dockerfile)
# # Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    apt-utils \
                    autoconf \
                    build-essential \
                    bzip2 \
                    ca-certificates \
                    curl \
                    wget \
                    sudo \
                    git \
                    libasound2 \
                    libcairo-gobject2 libcairo2 libcap2 libcrypt1 libcrypt-dev \
                    libcups2 libdbus-1-3 libdrm2 libfontconfig1 libgbm1 libgdk-pixbuf2.0-0 libgl1 libglib2.0-0 \
                    libgomp1 libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 libgtk-3-0 libnspr4 libnss3 libodbc1 \
                    libpam0g libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
                    libsm6 libsndfile1 \
                    libuuid1 libx11-6 libx11-xcb1 libxcb-dri3-0 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
                    libxext6 libxfixes3 libxft2 libxi6 libxinerama1 libxrandr2 libxrender1 libxt6 libxtst6 libxxf86vm1 \
                    linux-libc-dev \
                    make net-tools procps zlib1g \
                    libtool \
                    lsb-release \
                    netbase \
                    pkg-config \
                    python3-pip \
                    unzip \
                    xvfb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# MATLAB
# Install patched glibc - See https://github.com/mathworks/build-glibc-bz-19329-patch
# Note: base-dependencies.txt includes libcrypt-dev and linux-libc-dev to enable installation of patched -dev packages
# WORKDIR /packages
# RUN apt-get update && apt-get clean && apt-get autoremove && \
#     wget -q https://github.com/mathworks/build-glibc-bz-19329-patch/releases/download/ubuntu-focal/all-packages.tar.gz && \
#     tar -x -f all-packages.tar.gz \
#     --exclude glibc-*.deb \
#     --exclude libc6-dbg*.deb
# RUN apt-get install ./*.deb && \
#     rm -fr /packages
# WORKDIR /

# Copyright 2019 - 2022 The MathWorks, Inc.

# To specify which MATLAB release to install in the container, edit the value of the MATLAB_RELEASE argument.
# Use lower case to specify the release, for example: ARG MATLAB_RELEASE=r2021b
ARG MATLAB_RELEASE=r2023a

# When you start the build stage, this Dockerfile by default uses the Ubuntu-based matlab-deps image.
# To check the available matlab-deps images, see: https://hub.docker.com/r/mathworks/matlab-deps
# FROM mathworks/matlab-deps:${MATLAB_RELEASE}

# Declare the global argument to use at the current build stage
ARG MATLAB_RELEASE

# Install mpm dependencies & tini
RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
    tini \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

# Run mpm to install MATLAB in the target location and delete the mpm installation afterwards.
# If mpm fails to install successfully then output the logfile to the terminal, otherwise cleanup.
RUN wget -q https://www.mathworks.com/mpm/glnxa64/mpm \ 
    && chmod +x mpm \
    && ./mpm install \
    --release=${MATLAB_RELEASE} \
    --destination=/opt/matlab \
    --products MATLAB Curve_Fitting_Toolbox Parallel_Computing_Toolbox Statistics_and_Machine_Learning_Toolbox \
        Image_Processing_Toolbox Optimization_Toolbox \
    || (echo "MPM Installation Failure. See below for more information:" && cat /tmp/mathworks_root.log && false) \
    && rm -f mpm /tmp/mathworks_root.log \
    && ln -s /opt/matlab/bin/matlab /usr/local/bin/matlab \
    && rm /opt/matlab/sys/os/glnxa64/libstdc++*
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/opt/matlab/extern/bin/glnxa64:/opt/matlab/sys/os/glnxa64

# Add "matlab" user and grant sudo permission.
RUN adduser --shell /bin/bash --disabled-password --gecos "" matlab \
    && echo "matlab ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/matlab \
    && chmod 0440 /etc/sudoers.d/matlab

# One of the following 2 ways of configuring the license server to use must be
# uncommented.

# ARG LICENSE_SERVER
# Specify the host and port of the machine that serves the network licenses 
# if you want to bind in the license info as an environment variable. This 
# is the preferred option for licensing. It is either possible to build with 
# something like --build-arg LICENSE_SERVER=27000@MyServerName, alternatively
# you could specify the license server directly using
#       ENV MLM_LICENSE_FILE=27000@flexlm-server-name
# ENV MLM_LICENSE_FILE=$LICENSE_SERVER

# Alternatively you can put a license file into the container.
# You should fill this file out with the details of the license 
# server you want to use and uncomment the following line.
# COPY network.lic /opt/matlab/licenses/

# The following environment variables allow MathWorks to understand how this MathWorks 
# product (MATLAB Dockerfile) is being used. This information helps us make MATLAB even better. 
# Your content, and information about the content within your files, is not shared with MathWorks. 
# To opt out of this service, delete the environment variables defined in the following line. 
# See the Help Make MATLAB Even Better section in the accompanying README to learn more: 
# https://github.com/mathworks-ref-arch/matlab-dockerfile#help-make-matlab-even-better
# ENV MW_DDUX_FORCE_ENABLE=true MW_CONTEXT_TAGS=MATLAB:DOCKERFILE:V1

# Set user and work directory
# USER matlab
# WORKDIR /home/matlab
# ENTRYPOINT ["/usr/bin/tini", "--", "matlab"]
# CMD [""]

# Simulate SetUpFreeSurfer.sh
ENV FSL_DIR="/opt/fsl" \
    OS="Linux" \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA="" \
    FSF_OUTPUT_FORMAT="nii.gz" \
    FREESURFER_HOME="/usr/local/freesurfer/8.1.0"
ENV SUBJECTS_DIR="$FREESURFER_HOME/subjects" \
    FUNCTIONALS_DIR="$FREESURFER_HOME/sessions" \
    MNI_DIR="$FREESURFER_HOME/mni" \
    LOCAL_DIR="$FREESURFER_HOME/local" \
    MINC_BIN_DIR="$FREESURFER_HOME/mni/bin" \
    MINC_LIB_DIR="$FREESURFER_HOME/mni/lib" \
    MNI_DATAPATH="$FREESURFER_HOME/mni/data"
ENV PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    MNI_PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    PATH="$FREESURFER_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH"

# Installing freesurfer
COPY docker/files/freesurfer-exclude.txt /usr/local/etc/freesurfer-exclude.txt
RUN curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/8.1.0/freesurfer_ubuntu22-8.1.0_amd64.deb -o /tmp/freesurfer.deb \
    && dpkg -i /tmp/freesurfer.deb \
    && rm -f /tmp/freesurfer.deb \
    && ./${FREESURFER_HOME}/SetUpFreeSurfer.sh \
    && rm -rf /usr/local/freesurfer/8.1.0/trctrain \
    && rm -rf /usr/local/freesurfer/8.1.0/python \
    && rm -rf /usr/local/freesurfer/8.1.0/subjects \
    && rm -rf /usr/local/freesurfer/8.1.0/average \
    && rm -rf /usr/local/freesurfer/8.1.0/models \
    && if [ -f /usr/local/etc/freesurfer-exclude.txt ]; then \
        cd /usr/local/freesurfer/8.1.0 && \
        grep -v '^#' /usr/local/etc/freesurfer-exclude.txt | xargs -r rm -rf; \
    fi

# FSL
ENV FSLDIR="/opt/fsl" \
    PATH="/opt/fsl/bin:$PATH" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLLOCKDIR="" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLGECUDAQ="cuda.q" \
    LD_LIBRARY_PATH="/opt/fsl/lib:$LD_LIBRARY_PATH"

RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
        bc \
        dc \
        file \
        libfontconfig1 \
        libfreetype6 \
        libgl1-mesa-dev \
        libgl1-mesa-dri \
        libglu1-mesa-dev \
        libgomp1 \
        libice6 \
        libxcursor1 \
        libxft2 \
        libxinerama1 \
        libxrandr2 \
        libxrender1 \
        libxt6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Downloading FSL ..." \
    && curl -Ls https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/getfsl.sh | sh -s \
    && rm -rf /opt/fsl/data/atlases \
        /opt/fsl/data/first \
        /opt/fsl/data/mist \
        /opt/fsl/data/possum \
        /opt/fsl/data/standard/bianca \
        /opt/fsl/data/standard/tissuepriors \
        /opt/fsl/doc \
        /opt/fsl/etc/default_flobs.flobs \
        /opt/fsl/etc/fslconf \
        /opt/fsl/etc/js \
        /opt/fsl/etc/luts \
        /opt/fsl/etc/matlab \
        /opt/fsl/extras \
        /opt/fsl/include \
        /opt/fsl/python \
        /opt/fsl/refdoc \
        /opt/fsl/tcl \
        /opt/fsl/bin/FSLeyes

# Installing ANTs 2.3.3 (NeuroDocker build)
# Note: the URL says 2.3.4 but it is actually 2.3.3
ENV ANTSPATH="/opt/ants/bin"
ENV PATH="${ANTSPATH}:$PATH"
WORKDIR /opt/ants
RUN curl -sSL "https://github.com/ANTsX/ANTs/releases/download/v2.6.2/ants-2.6.2-ubuntu-22.04-X64-gcc.zip" -o ants.zip \
    && unzip ants.zip \
    && mv ants-2.6.2/* . \
    && rmdir ants-2.6.2 \
    && rm ants.zip

WORKDIR /
# GPUFIT
RUN curl -sSLO "https://github.com/ironictoo/Gpufit/releases/download/1.3/Gpufit_1.3.0_linux.zip" \
    && unzip -d /opt/Gpufit Gpufit*.zip && rm /Gpufit*.zip && mv /opt/Gpufit/Gpufit_1.2.0/* /opt/Gpufit/
    # && rmdir /opt/Gpufit/Gpufit_1.3.0_linux
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/Gpufit/matlab64/matlab
ENV GPUFIT_PATH="/opt/Gpufit/matlab64"

# HD-BET
RUN curl -sSLO "https://github.com/MIC-DKFZ/HD-BET/archive/refs/heads/master.zip" \
    && unzip -d /opt/HD-BET *master.zip && mv /opt/HD-BET/HD-BET-master/* /opt/HD-BET && rm -rf /opt/HD-BET/HD-BET-master && cd /opt/HD-BET && pip install --no-cache-dir -e . \
    && sed -i 's/~/\//' /opt/HD-BET/HD_BET/paths.py \
    && mkdir -p /hd-bet_params/release_2.0.0 \
    && chmod -R 777 /hd-bet_params/release_2.0.0 \
    && cd /hd-bet_params/release_2.0.0 \
    && curl -sSLo /hd-bet_params/release_v1.5.0.zip "https://zenodo.org/records/14445620/files/release_v1.5.0.zip?download=1" \
    && unzip /hd-bet_params/release_v1.5.0.zip -d /hd-bet_params/release_2.0.0 \
    && rm /hd-bet_params/release_v1.5.0.zip && chmod -R 777 /hd-bet_params/release_2.0.0

# AUTO AIF
RUN git clone --depth 1 https://github.com/petmri/vascular_function.git /opt/vascular_function \
    && cd /opt/vascular_function \
    && grep -vE '^(cupy|tensorrt_cu12)' requirements.txt > filtered-requirements.txt \
    && pip install --no-cache-dir -r filtered-requirements.txt \
    && rm filtered-requirements.txt

# ROCKETSHIP
RUN curl -sSLO "https://github.com/petmri/ROCKETSHIP/archive/refs/heads/dev.zip" \
    && unzip -d /opt/ROCKETSHIP *dev.zip && rm /dev.zip

# REST OF THIS
COPY . .
ENV MPLCONFIGDIR="/matplotlib"

RUN python3 -m pip install --no-cache-dir -r requirements.txt && python3 -m pip cache purge && \
    rm -f *.zip
