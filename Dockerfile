# syntax=docker/dockerfile:1

FROM nvidia/cuda:12.0.0-base-ubuntu22.04
CMD nvidia-smi


# # From fmriprep (https://github.com/nipreps/fmriprep/blob/master/Dockerfile)
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

# Installing freesurfer
COPY docker/files/freesurfer7.3-exclude.txt /usr/local/etc/freesurfer7.3-exclude.txt
RUN curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.3.2/freesurfer-linux-ubuntu22_amd64-7.3.2.tar.gz \
    | tar zxv --no-same-owner -C /opt --exclude-from=/usr/local/etc/freesurfer7.3-exclude.txt

# # Simulate SetUpFreeSurfer.sh
ENV FSL_DIR="/opt/fsl-6.0.5.2" \
    OS="Linux" \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA="" \
    FSF_OUTPUT_FORMAT="nii.gz" \
    FREESURFER_HOME="/opt/freesurfer"
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
    && find /opt/fsl-6.0.5.2/data/standard -type f -not -name "MNI152_T1_2mm_brain.nii.gz" -delete
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
        --exclude "antsA*" \
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
RUN curl -sSLO "https://github.com/ironictoo/Gpufit/releases/download/1.3/ubuntu-22.04-x64-cuda-11.7.0.zip" \
    && unzip -d /opt/Gpufit *11.7.0.zip
ENV GPUFIT_PATH="/opt/Gpufit"

# ROCKETSHIP
RUN curl -sSLO "https://github.com/petmri/ROCKETSHIP/archive/77b086ed24f15a3097aa6ef0c572c59ce20061e8.zip" \
    && unzip -d /opt/ROCKETSHIP *20061e8.zip

# HD-BET
RUN curl -sSLO "https://github.com/MIC-DKFZ/HD-BET/archive/refs/heads/master.zip" \
    && unzip -d /opt/HD-BET *master.zip && cd /opt/HD-BET/HD-BET-master && pip install --no-cache-dir -e . \
    && mkdir ~/hd-bet_params && cd ~/hd-bet_params && curl -sSLo '#1.model' \
    https://zenodo.org/record/2540695/files/[0-4].model?download=1

# THIS
COPY . .

RUN python3 -m pip install --no-cache-dir -r requirements.txt && python3 -m pip cache purge && \
    rm -f *.zip

# MATLAB
