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

# What is the easiest way to describe the lens for this grammar?

Store(lens="Uploaders")+":" + Sp() + List(item_lens=Dependancy, sep_lens=(","+OptSp()+Opt(NL+Indent))

# Maybe have simple field as default.
Store("field", lens="Source"|"Section"|"Priority"|"Maintainer")
#
# This is just an examnple of where I'd like to be with the lens serialisation idea.
#

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


class Iface :
  # List() could be an ordered dict.
  lens = "iface" + St("name") + St("address_family",match=["inet","other"]) + St("mode",match=["static","dhcp"]) + EOL() +
            List("attributes", Indent() + St("name") + List("args", Store()) + EOL())

class Auto :
  lens = "auto" + List("interfaces", Store())   # Here Store() means append a keyword match to the specified list.

class NetworkInterfaces :
  BlankLine = ...
  Comment = ...
  lens = ZeroOrMore(Iface | Auto | BlankLine | Comment)

"""
NOTES

Elements can be lenses and helper functions that return lenses
"""

CONFIG_EXAMPLE = """

# interfaces
iface eth0 inet static
    address 67.207.128.159
    netmask 255.255.255.0
    gateway 67.207.128.1
    dns-nameservers 67.207.128.4 67.207.128.5

# logrotate
/var/log/btmp /some/other/file {
    missingok
    monthly
    create 0660 root utmp
    rotate 1
}

iface wlan0 inet static
    address 1.2.3.4
    netmask 255.255.255.0
    gateway 67.207.128.23
    dns-nameservers 67.207.128.4 67.207.128.5

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

class NetworkInterface :
  lens = ... 

class LogFileSettings :
  lens = ...

class DebianPackageInfo :
  lens = ...

class Configuration :
  lens = ZeroOrMore(empty) + ZeroOrMore(empty | comment | NetworkInterface | LogFileSettings | DebianPackageInfo) + ZeroOrMore(empty)

#
# Main
#
configuration = Configuration.get(CONFIG_EXAMPLE)
configuration.network_interfaces.wlan0.dns_nameservers.append("123.123.0.1")
configuration.debian_packages["libconfig-model-perl"].dependancies[1:1] = [Dependancy("python", version="2.6", relation=">=")]
new_config = configuration.put()

# Basically, a lens can be represented by a class, and an instance may hold parsed state, necessary to reconstruct
# the original input plus any changes.

# Additionally, we could drive the applications with the objects

#
# Apache Example
#

apache_config = [GET from config file]
new_virtual_host = VirtualHost(name="www.somesite.com", aliases=["x","y","z"])
apache_config.add(new_virtual_host)

another_vhost = apache_config.get("www.another.com") # Praps get is some sort of simple query function.
another_vhost.add()  # And add is some kind of insert.
