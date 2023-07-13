FROM debian:stretch-slim
LABEL MAINTAINER "Lorenzo Bernardi <docker@bernardi.be>"

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG C.UTF-8

# Use backports to avoid install some libs with pip
RUN echo 'deb http://archive.debian.org/debian stretch-backports main' > /etc/apt/sources.list.d/backports.list && \
    sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/.*stretch-updates.*//g' /etc/apt/sources.list

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dirmngr \
    fonts-noto-cjk \
    gnupg \
    libssl1.0-dev \
    node-less \
    python3-num2words \
    python3-pip \
    python3-phonenumbers \
    python3-pyldap \
    python3-qrcode \
    python3-renderpm \
    python3-setuptools \
    python3-slugify \
    python3-vobject \
    python3-watchdog \
    python3-xlrd \
    python3-xlwt \
    python3-pypdf2 \
    python3-psycopg2 \
    xz-utils \
    && case $(dpkg --print-architecture) in \
    amd64) wkhtml_deb="wkhtmltox_0.12.5-1.stretch_amd64.deb" ;; \
    armhf) wkhtml_deb="wkhtmltox_0.12.5-1.raspbian.stretch_armhf.deb" ;; \
    *) echo "Unsupported architecture $(dpkg --print-architecture)"; exit 1 ;; \
    esac \
    && curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/${wkhtml_deb} \
    # && echo '7e35a63f9db14f93ec7feeb0fce76b30c08f2057 wkhtmltox.deb' | sha1sum -c - \
    && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
    && pip3 install pywebdav \
    && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# install latest postgresql-client
RUN for i in {1..8}; do mkdir -p "/usr/share/man/man$i"; done \
    && echo 'deb http://apt-archive.postgresql.org/pub/repos/apt/ stretch-pgdg-archive main' > /etc/apt/sources.list.d/pgdg.list \
    && GNUPGHOME="$(mktemp -d)" \
    && export GNUPGHOME \
    && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
    && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
    && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
    && gpgconf --kill all \
    && rm -rf "$GNUPGHOME" \
    && apt-get update  \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -f /etc/apt/sources.list.d/pgdg.list \
    && rm -rf /var/lib/apt/lists/*

# RUN  \
#         && apt-get update \
#         && apt-get -y install --no-install-recommends postgresql-client \
#         && rm -rf /var/lib/apt/lists/*

RUN curl -o python-pypdf.deb -sSL http://archive.debian.org/debian/pool/main/p/python-pypdf/python-pypdf_1.13-2_all.deb\
    && curl -o python-support.deb -sSL http://archive.debian.org/debian/pool/main/p/python-support/python-support_1.0.15_all.deb \
    && apt-get update \
    && apt-get -y install --no-install-recommends ./python-support.deb \
    && apt-get -y install --no-install-recommends python \
    && apt-get -y install --no-install-recommends ./python-pypdf.deb \
    && rm -rf /var/lib/apt/lists/* python-pypdf.deb

# Install Odoo
ENV ODOO_VERSION 8.0
ARG ODOO_RELEASE=20171001
ARG ODOO_SHA=c41c6eaf93015234b4b62125436856a482720c3d
RUN curl -o odoo.deb -sSL http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb \
    && echo "${ODOO_SHA} odoo.deb" | sha1sum -c - \
    && apt-get update \
    && apt-get -y install --no-install-recommends ./odoo.deb \
    && rm -rf /var/lib/apt/lists/* odoo.deb

# Copy entrypoint script and Odoo configuration file
COPY ./apps/odoo/entrypoint.sh /
COPY ./apps/odoo/odoo.conf /etc/odoo/

# Mount /var/lib/odoo to allow restoring filestore and /mnt/extra-addons for users addons
RUN chown odoo /etc/odoo/odoo.conf \
    && mkdir -p /mnt/extra-addons \
    && chown -R odoo /mnt/extra-addons
VOLUME ["/var/lib/odoo", "/mnt/extra-addons"]

# Expose Odoo services
EXPOSE 8069 8071 8072

# Set the default config file
ENV ODOO_RC /etc/odoo/odoo.conf

COPY ./apps/odoo/wait-for-psql.py /usr/local/bin/wait-for-psql.py

# Set default user when running the container
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]

LABEL org.opencontainers.image.source="https://github.com/odoo/docker"
