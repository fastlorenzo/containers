target "docker-metadata-action" {}

variable "APP" {
  default = "kopia"
}

variable "VERSION" {
  // renovate: datasource=repology depName=alpine_3_22/kopia versioning=loose
  default = "0.19.0-r5"
}

variable "SOURCE" {
  default = "https://github.com/kopia/kopia"
}

group "default" {
  targets = ["image-local"]
}

target "image" {
  inherits = ["docker-metadata-action"]
  args = {
    VERSION = "${VERSION}"
  }
  labels = {
    "org.opencontainers.image.source" = "${SOURCE}"
  }
}

target "image-local" {
  inherits = ["image"]
  output = ["type=docker"]
  tags = ["${APP}:${VERSION}"]
}

target "image-all" {
  inherits = ["image"]
  platforms = [
    "linux/amd64",
    "linux/arm64"
  ]
}
