#
# These are just examples, thinking out loud, of where I'd like to be with the lens serialisation idea.
#

CONFIG_EXAMPLE = """

# debian
Source: libconfig-model-perl
Section: perl
Uploaders: Dominique Dumont <dominique.dumont@xx.yyy>,
           gregor herrmann <gregoa@xxx.yy>
Priority: optional
Build-Depends: debhelper (>= 7.0.0),
               perl-modules (>= 5.10) | libmodule-build-perl
Build-Depends-Indep: perl (>= 5.8.8-12), libcarp-assert-more-perl,
                     libconfig-tiny-perl, libexception-class-perl,
                     libparse-recdescent-perl (>= 1.90.0),
                     liblog-log4perl-perl (>= 1.11)
Maintainer: Debian Perl Group <pkg-perl-maintainers@xx>
Standards-Version: 3.8.2
Vcs-Svn: svn://svn.debian.org/svn/pkg-perl/trunk/libconfig-model-perl
Vcs-Browser: http://svn.debian.org/viewsvn/pkg-perl/trunk/libconfig-model-perl/
Homepage: http://search.cpan.org/dist/Config-Model/

"""

# Extract an instance of DebianPackage from the string.
package = get(CONFIG_EXAMPLE, DebianPackage)

print(package.build_depends_indep[0][0].required_version)
# -> 5.8.8-12
print(package.build_depends_indep[1][0].required_version)
# -> None

# [Modify package]
package.maintainer = "Joe Bloggs <joe@bloggs.com>"

put(CONFIG_EXAMPLE, package)


CONFIG_EXAMPLE = """

# interfaces
iface eth0 inet static
    address 67.207.128.159
    netmask 255.255.255.0
    gateway 67.207.128.1
    dns-nameservers 67.207.128.4 67.207.128.5

iface wlan0 inet static
    address 1.2.3.4
    netmask 255.255.255.0
    gateway 67.207.128.23
    dns-nameservers 67.207.128.4 67.207.128.5

auto eth0

"""

interfaces = get(CONFIG_EXAMPLE, NetworkInterfaces)

print(interfaces.eth0.dns_nameservers[1])
# -> "67.207.128.5"

print(interfaces.wlan0.method)
# -> "static"

print(interfaces.is_auto("wlan0"))
# -> False

# Modify
interfaces.set_auto("wlan0")

eth1 = NetworkInterface(address="...", netmask="...")
eth1.dns_nameservers = ["...", "..."]

interfaces.add(eth1)

put(CONFIG_EXAMPLE, interfaces)


CONFIG_EXAMPLE = """
Listen 80
ServerRoot /usr/local/apache2
DocumentRoot /usr/local/webroot

ServerName localhost:80
ServerAdmin admin@localhost

PidFile logs/httpd.pid

Timeout 300

KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 15

User nobody
Group nobody

<IfModule prefork.c>
  MaxClients 150
  StartServers 5
  MinSpareServers 5
  MaxSpareServers 10
  MaxRequestsPerChild 0
</IfModule>

LoadModule info_module modules/mod_info.so
LoadModule dir_module modules/mod_dir.so
LoadModule php4_module modules/libphp4.so

<Location />
  <IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/css
    <IfModule mod_headers.c>
      Header append Vary User-Agent
    </IfModule>
  </IfModule>
</Location>

<Directory />
  Options FollowSymLinks
  AllowOverride None
  order allow,deny
  deny from all
</Directory>
"""

apache_config = get(CONFIG_EXAMPLE, ApacheConfig)

print(apache_config.keep_alive) # -> True

print(apache_config.modules["info_module"]) # -> "modules/mod_info.so"

print(apache_config.locations["/"].module_conditions["mod_deflate.c"].add_output_filter_by_type)
# -> DEFLATE text/html text/plain text/css
