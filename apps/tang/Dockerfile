# syntax=docker/dockerfile:1

# Minimal Tang (Network-Bound Disk Encryption server) image.
#
# Tang is not packaged in Alpine, so it is compiled from source against
# Alpine's libjose/http-parser. tangd is an inetd-style service (it reads a
# request on stdin and writes the response on stdout), so busybox inetd
# fronts it on a TCP port. tangd-keygen execs the `jose` CLI to mint keys.
#
# A throwaway Alpine stage compiles Tang and assembles a tiny rootfs that is
# copied into a FROM scratch final image so it fits on constrained flash
# (e.g. MikroTik RouterOS containers on internal NAND).

FROM docker.io/library/alpine:3.22 AS build
ARG VERSION
USER root

RUN apk add --no-cache \
        binutils \
        build-base \
        busybox \
        curl \
        http-parser-dev \
        jose \
        jose-dev \
        libjose \
        meson \
        ninja

# Build and install Tang into a staging DESTDIR.
RUN set -eux; \
    cd /tmp; \
    curl -fsSL "https://github.com/latchset/tang/archive/refs/tags/v${VERSION}.tar.gz" \
        -o tang.tar.gz; \
    tar xzf tang.tar.gz; \
    cd "tang-${VERSION}"; \
    meson setup build \
        --prefix=/usr \
        --localstatedir=/var \
        -Duser=root \
        -Dgroup=root; \
    ninja -C build; \
    DESTDIR=/dest meson install -C build

COPY ./entrypoint.sh /src/entrypoint.sh

# Assemble the minimal rootfs that the scratch image will use.
RUN set -eux; \
    R=/rootfs; \
    mkdir -p "$R/usr/libexec" "$R/usr/bin" "$R/bin" "$R/etc" "$R/var/db/tang"; \
    # minimal passwd/group so tangd-keygen's chown root:root resolves \
    echo 'root:x:0:0:root:/:/bin/sh' > "$R/etc/passwd"; \
    echo 'root:x:0:' > "$R/etc/group"; \
    # Tang binaries + scripts \
    cp /dest/usr/libexec/tangd             "$R/usr/libexec/"; \
    cp /dest/usr/libexec/tangd-keygen      "$R/usr/libexec/"; \
    cp /dest/usr/libexec/tangd-rotate-keys "$R/usr/libexec/" 2>/dev/null || true; \
    cp /dest/usr/bin/tang-show-keys        "$R/usr/bin/" 2>/dev/null || true; \
    # jose CLI is execed by tangd-keygen at runtime \
    cp /usr/bin/jose "$R/usr/bin/jose"; \
    # busybox provides sh, inetd, chmod, chown and every other applet \
    cp /bin/busybox "$R/bin/busybox"; \
    # Resolve and copy every shared library the binaries need \
    for b in "$R/usr/libexec/tangd" "$R/usr/bin/jose" "$R/bin/busybox"; do \
      ldd "$b" 2>/dev/null | awk '/=>/ {print $3} /ld-musl|ld-linux/ {print $1}'; \
    done | sort -u | while read -r lib; do \
      [ -f "$lib" ] || continue; \
      mkdir -p "$R$(dirname "$lib")"; \
      cp -L "$lib" "$R$lib"; \
    done; \
    # busybox applet symlinks (sh, inetd, chmod, chown, ...) \
    chroot "$R" /bin/busybox --install -s /bin; \
    # entrypoint \
    install -m 0755 /src/entrypoint.sh "$R/entrypoint.sh"; \
    # strip to shrink \
    find "$R" -type f \( -name '*.so*' -o -path '*/libexec/*' -o -name busybox -o -name jose \) \
      -exec strip --strip-unneeded {} + 2>/dev/null || true; \
    echo '=== extracted rootfs size ==='; du -sh "$R"; \
    echo '=== largest files ==='; find "$R" -type f -exec du -h {} + | sort -h | tail -20

FROM scratch
ARG VERSION
LABEL org.opencontainers.image.title="tang"
COPY --from=build /rootfs/ /
# Tang advertisement/key-exchange port
EXPOSE 8080
ENTRYPOINT ["/bin/busybox", "sh", "/entrypoint.sh"]
