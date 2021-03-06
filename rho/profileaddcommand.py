#
# Copyright (c) 2009-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# pylint: disable=too-few-public-methods

""" ProfileAddCommand is used to create profiles that associate hosts
and authentication credentials
"""

from __future__ import print_function
import os
import sys
from collections import OrderedDict
from rho import utilities
from rho.clicommand import CliCommand
from rho.vault import get_vault
from rho.utilities import multi_arg, read_ranges
from rho.translation import _


def profile_exists(profile_list, profile_name):
    """ Checks whether a network profile already exists

    :param profile_list: A list of profile dictionaries
    :param profile_name: Name of a network profile to check for existence
    :returns: True if profile_name exists, False otherwise
    """
    profile_found = False
    for profile in profile_list:
        if profile.get('name') == profile_name:
            profile_found = True
            break
    return profile_found


def _save_profile(vault, new_profile, profiles_list):
    """ Write new profile in the related file

    :param vault: Vault object for writing encrypted data
    :param new_profile: New profile to be added to the profiles file
    :param profiles_list: A list of existing profiles dictionaries from the
        profiles file
    """

    utilities.ensure_config_dir_exists()

    profiles_list.append(new_profile)

    vault.dump_as_json_to_file(profiles_list, utilities.PROFILES_PATH)


class ProfileAddCommand(CliCommand):
    """
    This command is for creating new profiles
    based on hosts and the auths the user wants
    to associate.
    """

    def __init__(self):
        usage = _("usage: %prog profile add [options]")
        shortdesc = _("add a network profile")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile - REQUIRED"))
        self.parser.add_option("--hosts", dest="hosts", action="callback",
                               callback=multi_arg,
                               metavar="HOSTS", default=[],
                               help=_("IP range to scan."
                                      " See 'man rho' for supported formats."))
        self.parser.add_option("--sshport", dest="sshport", metavar="SSHPORT",
                               help=_("SSHPORT for connection; default=22"))
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                               action="callback", callback=multi_arg,
                               default=[], help=_("auth class to "
                                                  "associate with profile"))
        self.parser.add_option("--vault", dest="vaultfile", metavar="VAULT",
                               help=_("file containing vault password for"
                                      " scripting"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.hosts:
            self.parser.print_help()
            sys.exit(1)

        if not self.options.auth:
            self.parser.print_help()
            sys.exit(1)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

        if hasattr(self.options, 'sshport') \
           and self.options.sshport is not None:
            ssh_port = self.options.sshport
            try:
                ssh_port = utilities.validate_port(ssh_port)
                self.options.sshport = ssh_port
            except ValueError as port_error:
                print(str(port_error))
                self.parser.print_help()
                sys.exit(1)
        else:
            self.options.sshport = 22

    # pylint: disable=too-many-locals
    def _do_command(self):
        vault = get_vault(self.options.vaultfile)
        profiles_list = []
        ssh_port = self.options.sshport

        if os.path.isfile(utilities.PROFILES_PATH):
            profiles_list = vault.load_as_json(utilities.PROFILES_PATH)
            profile_found = profile_exists(profiles_list, self.options.name)
            if profile_found:
                print(_("Profile '%s' already exists.") % self.options.name)
                sys.exit(1)

        range_list = read_ranges(self.options.hosts)

        if not os.path.isfile(utilities.CREDENTIALS_PATH):
            print(_('No credentials exist yet.'))
            sys.exit(1)

        creds = []
        cred_list = vault.load_as_json(utilities.CREDENTIALS_PATH)
        for auth in self.options.auth:
            for auth_item in auth.strip().split(","):
                valid = False
                for cred in cred_list:
                    if cred.get('name') == auth:
                        valid = True
                        # add the uuids of credentials
                        store_cred = {'id': cred.get('id'),
                                      'name': cred.get('name')}
                        creds.append(store_cred)

                if not valid:
                    print("Auth " + auth_item + " does not exist")
                    sys.exit(1)

        new_profile = OrderedDict([("name", self.options.name),
                                   ("hosts", range_list),
                                   ("ssh_port", str(ssh_port)),
                                   ("auth", creds)])

        _save_profile(vault, new_profile, profiles_list)
        print(_('Profile "%s" was added' % self.options.name))
