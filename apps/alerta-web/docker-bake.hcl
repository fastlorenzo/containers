target "docker-metadata-action" {}

variable "APP" {
  default = "openclaw"
}

variable "VERSION" {
  // renovate: datasource=docker depName=docker.io/alerta/alerta-web
  default = "9.1.0"
}

variable "SOURCE" {
  default = "https://github.com/alerta/docker-alerta"
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
    "linux/amd64"
  ]
}
