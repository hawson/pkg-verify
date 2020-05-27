# pkg-verify
Verify Arch Linux packages, including checksums

This code is released as public domain code.  Have fun.  Send a post card.

THe Arch Linux package manager stores information about the contents
of all files in package in the "mtree" forma.  These files reside in
/var/lib/pacman/local/<pkg>/mtree.  The contents are used when verifying a
package via "pacman -Qkk", except that any checksum information about the
file is completely ignored.  As a check to see if a file is corrupted,
the checksums are incredibly useful, and not having those in pacman
directly seems like an oversight.

Other package managers that store similar metadata (such as RPM), can
use the checksum data to verify that the contents of the file are the
same or different than they were at install time.  This is not a security
measure; this is a data integrity check.

Similar to the output from RPM, a verification line looks like this:

  .........     /usr/share/man/man5/whois.conf.5.gz
  |||||||||
  ||||||||+-- P caPabilities differ  (NOT USED)'''
  |||||||+--- T mTime differs
  ||||||+---- G Group ownership differs
  |||||+----- U User ownership differs
  ||||+------ L readLink(2) path mismatch
  |||+------- D Device major/minor number mismatch (NOT USED)
  ||+-------- 5 digest (formerly MD5 sum) differs MD5 and sha256 both)
  |+--------- M Mode differs (includes permissions and file type)
  +---------- S file Size differs

Normally, a line is printed only for files that fail all tests.

With -v, all package contents are printed, even if they pass all checks.
With -vv, all contents are printed, along with piles of debug information.

Certain directories present an interesting problem.  Many packages drop
files into, e.g. `/usr/man/man1` and also claim `/usr` and `/usr/man`
as part of the package.  As result of this is that the mtime on the
directory is very often wrong for these "shared directories".  To keep
the noise level down, pkg-verify does *not* check mtimes on directories
by default.  If you wish to force these checks, use the "-T" CLI option.

Lastly, if you need to check files under an alternate root directory,
you can use the "-R <altroot>" option.


