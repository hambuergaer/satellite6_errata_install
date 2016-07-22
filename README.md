# satellite6_errata_install

# Description

This script helps you to install Red Hat errata packages on your content hosts depending on the lifecycle environment where a host is assigned to.

If you don`t pass the option "--update-enhancement-errata" only security and bugfix errata will be applied to your hosts.

If you don`t pass the option "--update-host" you will only see a summary of applicabel errata per host.

If you pass the option "--write-log" a log file will be written in ".errata_update_logs".

# Prerequisites
This script should be run on a host with hammer cli installed.
```
yum install -y rubygem-hammer_cli_csv rubygem-hammer_cli_foreman_bootdisk rubygem-hammer_cli_gutterball rubygem-hammer_cli_foreman_tasks rubygem-hammer_cli_katello rubygem-hammer_cli_foreman rubygem-hammer_cli
```
