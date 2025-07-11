FROM bitnami/redmine:6.0.6-debian-12-r2

# RUN install_packages build-essential default-libmysqlclient-dev libpq-dev libmagickwand-dev

WORKDIR /opt/bitnami/redmine

COPY ./apps/redmine/redmine_openid_connect /opt/bitnami/redmine/plugins/redmine_openid_connect
RUN bundle config set --local deployment 'false' && \
    bundle install && \
    bundle config set --local deployment 'true'

LABEL org.opencontainers.image.source="https://github.com/bitnami/containers"
