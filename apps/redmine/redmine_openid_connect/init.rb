require 'redmine'
require_relative 'redmine_openid_connect/application_controller_patch'
require_relative 'redmine_openid_connect/account_controller_patch'
require_relative 'redmine_openid_connect/users_controller_patch'
require_relative 'redmine_openid_connect/hooks'

Redmine::Plugin.register :redmine_openid_connect do
  name 'Redmine Openid Connect plugin'
  author 'Alfonso Juan Dillera / Markus M. May'
  description 'OpenID Connect implementation for Redmine'
  version '0.9.6'
  url 'https://github.com/eea/redmine_openid_connect'
  author_url 'http://github.com/adillera'

  settings :default => { 'empty' => true }, partial: 'settings/redmine_openid_connect_settings'
end

ApplicationController.prepend(RedmineOpenidConnect::ApplicationControllerPatch)
AccountController.prepend(RedmineOpenidConnect::AccountControllerPatch)
UsersController.prepend(RedmineOpenidConnect::UsersControllerPatch)
