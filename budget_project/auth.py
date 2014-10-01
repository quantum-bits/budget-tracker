from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

#from ldap.cidict import cidict
#import ldap
import re
import smtplib

MX_HOST='barracuda.taylor.edu'

LDAP_SERVER='ldap://campus.tayloru.edu'
BASE_DN='DC=campus,DC=tayloru,DC=edu'
# BASE_DN='OU=User Accounts,DC=campus,DC=tayloru,DC=edu'
# FILTER='(sn=nurkkala)'
# FILTER='(sAMAccountName=thnurkkala)'
# ATTRS=['sn', 'cn', 'mail', 'displayName']

def is_in_ldap_results(results, key, value):
    """In results returned from LDAP search, check that there is some result that contains
    a key with a given value.
    """
    for dn, data in results:
        if dn is None:
            continue
        if key in data:
            if value.lower() in [ v.lower() for v in data.get(key) ]:
                return True
    return False

def extract_scalar_ldap_value(results, key):
    """Extract the value for key from LDAP results. There must be only one record that
    matches key and its value must be a length-one list.
    """
    value = None
    for dn, data in results:
        if dn is None:
            continue
        if key in data:
            if value is not None:
                raise RuntimeError("More than one result matches key in '{0}'".format(results))
            value_list = data.get(key)
            if len(value_list) != 1:
                raise RuntimeError("Multiple values for '{0}' in '{1}'".format(key, value_list))
            value = value_list[0]
    return value

def authenticate_ldap_by_account(auth_acct, auth_pass, check_acct=None):
    """Authenticate account and password against the campus LDAP server (MS AD). The
    account name should be a user's account name (e.g., john_smith), not an e-mail
    address. If the account name is authentic, return a dictionary containing first name
    and last name. If not, return None.
    """
    if check_acct is None:
        check_acct = auth_acct

    value = None

    try:
        con = ldap.initialize(LDAP_SERVER)
        # Required for Active Directory when searching from the domain level (i.e.,
        # DC=campus,DC=tayloru,DC=edu) without an organizational unit (e.g., OU=User
        # Accounts).
        con.set_option(ldap.OPT_REFERRALS, 0)

        con.simple_bind_s('{0}@campus.tayloru.edu'.format(auth_acct), auth_pass)

        results = con.search_s(BASE_DN, ldap.SCOPE_SUBTREE,
                               '(sAMAccountName={0})'.format(auth_acct),
                               ['givenName', 'sn', 'cn', 'mail', 'sAMAccountName'])

        if is_in_ldap_results(results, 'sAMAccountName', check_acct):
            first_name = extract_scalar_ldap_value(results, 'givenName')
            last_name = extract_scalar_ldap_value(results, 'sn')
            value = { 'first_name': first_name, 'last_name': last_name }
    except ldap.LDAPError as e:
        pass
    finally:
        con.unbind()

    return value


class CampusLDAPBackend(ModelBackend):

    def authenticate(self, username=None, password=None):
        """Authenticate using LDAP. Find or create the associated Django user."""

        username = re.sub(r'@.*', '', username) # Strip e-mail domain if present
        auth_info = authenticate_ldap_by_account(username, password)

        if auth_info is None:
            return None

        try:
            # Try to find existing user with this e-mail address.
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create a new user.
            user = User(username=username,
                        email="{0}@taylor.edu".format(username),
                        first_name=auth_info['first_name'],
                        last_name=auth_info['last_name'])
            user.set_unusable_password()
            user.save()
        return user

def is_valid_taylor_email(addr, debug=False):
    """Return boolean indicating whether an e-mail address is valid in the Taylor domain.
    """
    conn = smtplib.SMTP(MX_HOST)
    if debug:
        conn.set_debuglevel(True)
    conn.ehlo()
    conn.docmd('MAIL FROM:', '<campusrec@taylor.edu>')
    code, msge = conn.docmd('RCPT TO:', '<{0}>'.format(addr))
    conn.quit()
    return code == 250


class FakeBackend(ModelBackend):
    """Fake authentication backend for testing."""
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        else:
            return None
