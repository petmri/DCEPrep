# syntax=docker/dockerfile:1

FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04


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

ENV DEBIAN_FRONTEND="noninteractive" \
    LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

# FSL 6.0.5.2
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
           sudo \
           wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Downloading FSL ..." \
    && mkdir -p /opt/fsl-6.0.5.2 \
    # && curl -fsSLA "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0" --retry 5 https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-6.0.5.2-centos7_64.tar.gz \
    && wget -qO- https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-6.0.5.2-centos7_64.tar.gz \
    | tar -xz -C /opt/fsl-6.0.5.2 --strip-components 1 \
    --exclude "fsl/config" \
    --exclude "fsl/data/atlases" \
    --exclude "fsl/data/first" \
    --exclude "fsl/data/mist" \
    --exclude "fsl/data/possum" \
    --exclude "fsl/data/standard/bianca" \
    --exclude "fsl/data/standard/tissuepriors" \
    --exclude "fsl/doc" \
    --exclude "fsl/etc/default_flobs.flobs" \
    --exclude "fsl/etc/fslconf" \
    --exclude "fsl/etc/js" \
    --exclude "fsl/etc/luts" \
    --exclude "fsl/etc/matlab" \
    --exclude "fsl/extras" \
    --exclude "fsl/include" \
    # --exclude "fsl/lib/libgfor*" \
    # --exclude "fsl/lib/openblas*" \
    --exclude "fsl/python" \
    --exclude "fsl/refdoc" \
    # --exclude "fsl/src" \
    --exclude "fsl/tcl" \
    --exclude "fsl/bin/FSLeyes" \
    && find /opt/fsl-6.0.5.2/bin -type f -not \( \
        # -name "applywarp" -or \
        # -name "bet" -or \
        # -name "bet2" -or \
        # -name "convert_xfm" -or \
        -name "fast" -or \
        -name "flirt" -or \
        # -name "fsl_regfilt" -or \
        -name "fslcpgeom" -or \
        -name "fslhd" -or \
        -name "fslinfo" -or \
        -name "fslmaths" -or \
        -name "fslmerge" -or \
        -name "fslnvols" -or \
        # -name "fslroi" -or \
        -name "fslsplit" -or \
        -name "fslstats" -or \
        # -name "imtest" -or \
        -name "mcflirt" \) -delete \
        # -name "melodic" -or \
        # -name "prelude" -or \
        # -name "remove_ext" -or \
        # -name "susan" -or \
        # -name "topup" -or \
        # -name "zeropad" \
    && find /opt/fsl-6.0.5.2/data/standard -type f -not -name "MNI152_T1_1mm.nii.gz" -delete
ENV FSLDIR="/opt/fsl-6.0.5.2" \
    PATH="/opt/fsl-6.0.5.2/bin:$PATH" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLLOCKDIR="" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLGECUDAQ="cuda.q" \
    LD_LIBRARY_PATH="/opt/fsl-6.0.5.2/lib:$LD_LIBRARY_PATH"

# Installing ANTs 2.3.3 (NeuroDocker build)
# Note: the URL says 2.3.4 but it is actually 2.3.3
ENV ANTSPATH="/opt/ants" \
    PATH="/opt/ants:$PATH"
WORKDIR $ANTSPATH
RUN curl -sSL "https://dl.dropbox.com/s/gwf51ykkk5bifyj/ants-Linux-centos6_x86_64-v2.3.4.tar.gz" \
    | tar -xzC $ANTSPATH --strip-components 1 \
        --exclude "A*" \
        --exclude "C*" \
        --exclude "D*" \
        --exclude "E*" \
        --exclude "F*" \
        --exclude "G*" \
        --exclude "I*" \
        --exclude "K*" \
        --exclude "L*" \
        --exclude "M*" \
        --exclude "N*" \
        --exclude "P*" \
        --exclude "R*" \
        --exclude "S*" \
        --exclude "T*" \
        --exclude "W*" \
        --exclude "w*" \
        # --exclude "antsA*" \
        --exclude "antsAI" \
        --exclude "antsASLProcessing*" \
        --exclude "antsAffine*" \
        --exclude "antsAlign*" \
        --exclude "antsApplyTransformsToPoints" \
        --exclude "antsAtroposN4*" \
        --exclude "antsB*" \
        --exclude "antsC*" \
        --exclude "antsI*" \
        --exclude "antsJ*" \
        --exclude "antsL*" \
        --exclude "antsM*" \
        --exclude "antsN*" \
        --exclude "antsS*" \
        --exclude "antsT*" \
        --exclude "antsU*" 

WORKDIR /
# GPUFIT
RUN curl -sSLO "https://github.com/ironictoo/Gpufit/releases/download/1.3/Gpufit_1.3.0_linux.zip" \
    && unzip -d /opt/Gpufit Gpufit*.zip && rm /Gpufit*.zip
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/Gpufit/Gpufit_1.2.0/matlab64/matlab
ENV GPUFIT_PATH="/opt/Gpufit/Gpufit_1.2.0/matlab64"

# ROCKETSHIP
RUN curl -sSLO "https://github.com/petmri/ROCKETSHIP/archive/refs/heads/dev.zip" \
    && unzip -d /opt/ROCKETSHIP *dev.zip && rm /dev.zip

# HD-BET
RUN curl -sSLO "https://github.com/MIC-DKFZ/HD-BET/archive/refs/heads/master.zip" \
    && unzip -d /opt/HD-BET *master.zip && cd /opt/HD-BET/HD-BET-master && pip install --no-cache-dir -e . \
    && sed -i 's/~/\//' HD_BET/paths.py && mkdir /hd-bet_params && cd /hd-bet_params \
    && curl -sSLo '#1.model' https://zenodo.org/record/2540695/files/[0-4].model?download=1 \
    && rm /master.zip

# AUTO AIF
RUN curl -sSLO "https://github.com/petmri/vascular_function/archive/refs/heads/optimize_input.zip" \
    && unzip -d /opt/vascular_function *optimize_input.zip && rm /optimize_input.zip

# pip requirements for this
COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir -r requirements.txt && python3 -m pip cache purge && \
    rm -f *.zip

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
ARG MATLAB_RELEASE=r2022a

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

# REST OF THIS
COPY . .
ENV MPLCONFIGDIR="/matplotlib"
