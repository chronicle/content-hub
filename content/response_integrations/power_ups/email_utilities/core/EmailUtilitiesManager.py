# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import re
import sys
import time

import dnslib

# only needed for arc
try:
    from authres import AuthenticationResultsHeader
except ImportError:
    pass

# only needed for ed25519 signing/verification
try:
    import nacl.encoding
    import nacl.signing
except ImportError:
    pass
import eml_parser
from dkim.crypto import (
    DigestTooLargeError,
    RSASSA_PKCS1_v1_5_sign,
    RSASSA_PKCS1_v1_5_verify,
    UnparsableKeyError,
    parse_pem_private_key,
    parse_public_key,
)
from netaddr import valid_ipv4, valid_ipv6

__all__ = [
    "ARC",
    "DKIM",
    "AuthresNotFoundError",
    "CV_Fail",
    "CV_None",
    "CV_Pass",
    "DKIMException",
    "InternalError",
    "KeyFormatError",
    "MessageFormatError",
    "NaClNotFoundError",
    "ParameterError",
    "Relaxed",
    "Simple",
    "ValidationError",
    "arc_sign",
    "arc_verify",
    "dkim_sign",
    "dkim_verify",
    "sign",
    "verify",
]

HASH_ALGORITHMS = {
    b"rsa-sha1": hashlib.sha1,
    b"rsa-sha256": hashlib.sha256,
    b"ed25519-sha256": hashlib.sha256,
}

ARC_HASH_ALGORITHMS = {b"rsa-sha256": hashlib.sha256}

# These values come from RFC 8017, section 9.2 Notes, page 46.
HASH_ID_MAP = {
    "sha1": "\x2b\x0e\x03\x02\x1a",
    "sha256": "\x60\x86\x48\x01\x65\x03\x04\x02\x01",
}

# for ARC
CV_Pass = b"pass"
CV_Fail = b"fail"
CV_None = b"none"


class InvalidCanonicalizationPolicyError(Exception):
    """The c= value could not be parsed."""


def strip_trailing_whitespace(content):
    return re.sub(b"[\t ]+\r\n", b"\r\n", content)


def compress_whitespace(content):
    return re.sub(b"[\t ]+", b" ", content)


def strip_trailing_lines(content):
    end = None
    while content.endswith(b"\r\n", 0, end):
        if end is None:
            end = -2
        else:
            end -= 2

    if end is None:
        return content + b"\r\n"

    end += 2
    if end == 0:
        return content

    return content[:end]


def unfold_header_value(content):
    return re.sub(b"\r\n", b"", content)


def correct_empty_body(content):
    if content == b"\r\n":
        return b""
    return content


class Simple:
    """Class that represents the "simple" canonicalization algorithm."""

    name = b"simple"

    @staticmethod
    def canonicalize_headers(headers):
        # No changes to headers.
        return [(x, headers[x]) for x in headers]
        # return headers

    @staticmethod
    def canonicalize_body(body):
        # Ignore all empty lines at the end of the message body.
        return strip_trailing_lines(body)


class Relaxed:
    """Class that represents the "relaxed" canonicalization algorithm."""

    name = b"relaxed"

    @staticmethod
    def canonicalize_headers(headers):
        # Convert all header field names to lowercase.
        # Unfold all header lines.
        # Compress WSP to single space.
        # Remove all WSP at the start or end of the field value (strip).
        return [
            (
                x.lower().rstrip(),
                compress_whitespace(unfold_header_value(headers[x])).strip() + b"\r\n",
            )
            for x in headers
        ]

    @staticmethod
    def canonicalize_body(body):
        # Remove all trailing WSP at end of lines.
        # Compress non-line-ending WSP to single space.
        # Ignore all empty lines at the end of the message body.
        return correct_empty_body(
            strip_trailing_lines(compress_whitespace(strip_trailing_whitespace(body))),
        )


class CanonicalizationPolicy:
    def __init__(self, header_algorithm, body_algorithm):
        self.header_algorithm = header_algorithm
        self.body_algorithm = body_algorithm

    @classmethod
    def from_c_value(cls, c):
        """Construct the canonicalization policy described by a c= value.

        May raise an C{InvalidCanonicalizationPolicyError} if the given
        value is invalid

        @param c: c= value from a DKIM-Signature header field
        @return: a C{CanonicalizationPolicy}
        """
        if c is None:
            c = b"simple/simple"
        m = c.split(b"/")
        if len(m) not in (1, 2):
            raise InvalidCanonicalizationPolicyError(c)
        if len(m) == 1:
            m.append(b"simple")
        can_headers, can_body = m
        try:
            header_algorithm = ALGORITHMS[can_headers]

            body_algorithm = ALGORITHMS[can_body]
        except KeyError as e:
            raise InvalidCanonicalizationPolicyError(e.args[0])
        return cls(header_algorithm, body_algorithm)

    def to_c_value(self):
        return b"/".join((self.header_algorithm.name, self.body_algorithm.name))

    def canonicalize_headers(self, headers):
        return self.header_algorithm.canonicalize_headers(headers)

    def canonicalize_body(self, body):
        return self.body_algorithm.canonicalize_body(body)


ALGORITHMS = dict((c.name, c) for c in (Simple, Relaxed))


class InvalidTagValueList(Exception):
    pass


class DuplicateTag(InvalidTagValueList):
    pass


class InvalidTagSpec(InvalidTagValueList):
    pass


def get_txt_dnspython(name, timeout=5):
    """Return a TXT record associated with a DNS name."""
    try:
        a = dns.resolver.query(
            name,
            dns.rdatatype.TXT,
            raise_on_no_answer=False,
            lifetime=timeout,
        )
        for r in a.response.answer:
            if r.rdtype == dns.rdatatype.TXT:
                return b"".join(list(r.items)[0].strings)
                # return "".join((r.items.strings))
    except dns.resolver.NXDOMAIN:
        pass
    return None


def get_txt_pydns(name, timeout=5):
    """Return a TXT record associated with a DNS name."""
    # Older pydns releases don't like a trailing dot.
    name = name.removesuffix(".")
    response = DNS.DnsRequest(name, qtype="txt", timeout=timeout).req()
    if not response.answers:
        return None
    for answer in response.answers:
        if answer["typename"].lower() == "txt":
            return "".join(answer["data"])
    return None


try:
    import dns.resolver

    _get_txt = get_txt_dnspython
except ImportError:
    try:
        import DNS

        DNS.DiscoverNameServers()
        _get_txt = get_txt_pydns
    except:
        raise


def parse_tag_value(tag_list):
    """Parse a DKIM Tag=Value list.

    Interprets the syntax specified by RFC6376 section 3.2.
    Assumes that folding whitespace is already unfolded.

    @param tag_list: A bytes string containing a DKIM Tag=Value list.
    """
    tags = {}

    tag_specs = tag_list.strip().split(b";")
    # tag_specs = tag_list.split(b';')
    # Trailing semicolons are valid.
    if not tag_specs[-1]:
        tag_specs.pop()
    for tag_spec in tag_specs:
        try:
            key, value = [x.strip() for x in tag_spec.split(b"=", 1)]
        except ValueError:
            raise InvalidTagSpec(tag_spec)
        if re.match(rb"^[a-zA-Z](\w)*", key) is None:
            raise InvalidTagSpec(tag_spec)
        if key in tags:
            raise DuplicateTag(key)
        tags[key] = value
    return tags


def get_txt(name, timeout=5):
    """Return a TXT record associated with a DNS name.

    @param name: The bytestring domain name to look up.
    """
    # pydns needs Unicode, but DKIM's d= is ASCII (already punycoded).
    try:
        # unicode_name = name.decode()
        unicode_name = name.decode()
    except UnicodeDecodeError:
        return None
    txt = _get_txt(unicode_name, timeout)

    if type(txt) is str:
        txt = txt.encode("utf-8")
    return txt


class HashThrough:
    def __init__(self, hasher, info=False):
        self.data = []
        self.hasher = hasher
        self.name = hasher.name
        self.info = info

    def update(self, data):
        if self.info:
            self.data.append(data)
        return self.hasher.update(data)

    def digest(self):
        return self.hasher.digest()

    def hexdigest(self):
        return self.hasher.hexdigest()

    def hashed(self):
        return b"".join(self.data)


def bitsize(x):
    """Return size of long in bits."""
    return len(bin(x)) - 2


class DKIMException(Exception):
    """Base class for DKIM errors."""


class InternalError(DKIMException):
    """Internal error in dkim module. Should never happen."""


class KeyFormatError(DKIMException):
    """Key format error while parsing an RSA public or private key."""


class MessageFormatError(DKIMException):
    """RFC822 message format error."""


class ParameterError(DKIMException):
    """Input parameter error."""


class ValidationError(DKIMException):
    """Validation error."""


class AuthresNotFoundError(DKIMException):
    """Authres Package not installed, needed for ARC"""


class NaClNotFoundError(DKIMException):
    """Nacl package not installed, needed for ed25119 signatures"""


class UnknownKeyTypeError(DKIMException):
    """Key type (k tag) is not known (rsa/ed25519)"""


def select_headers(headers, include_headers):
    """Select message header fields to be signed/verified.

    >>> h = [("from", "biz"), ("foo", "bar"), ("from", "baz"), ("subject", "boring")]
    >>> i = ["from", "subject", "to", "from"]
    >>> select_headers(h, i)
    [('from', 'baz'), ('subject', 'boring'), ('from', 'biz')]
    >>> h = [("From", "biz"), ("Foo", "bar"), ("Subject", "Boring")]
    >>> i = ["from", "subject", "to", "from"]
    >>> select_headers(h, i)
    [('From', 'biz'), ('Subject', 'Boring')]
    """
    sign_headers = []
    lastindex = {}
    for h in include_headers:
        assert h == h.lower()
        i = lastindex.get(h, len(headers))
        while i > 0:
            i -= 1
            if h == headers[i][0].lower():
                sign_headers.append(headers[i])
                break
        lastindex[h] = i
    return sign_headers


# FWS  =  ([*WSP CRLF] 1*WSP) /  obs-FWS ; Folding white space  [RFC5322]
FWS = rb"(?:(?:\s*\r?\n)?\s+)?"
RE_BTAG = re.compile(
    rb"([;\s]b" + FWS + rb"=)(?:" + FWS + rb"[a-zA-Z0-9+/=])*(?:\r?\n\Z)?",
)


def hash_headers(
    hasher,
    canonicalize_headers,
    headers,
    include_headers,
    sigheader,
    sig,
):
    """Update hash for signed message header fields."""
    sign_headers = select_headers(headers, include_headers)
    # The call to _remove() assumes that the signature b= only appears
    # once in the signature header
    # )
    cheaders = canonicalize_headers.canonicalize_headers(
        {b"dkim-signature": RE_BTAG.sub(b"\\1", sigheader[b"dkim-signature"])},
    )  # the dkim sig is hashed with no trailing crlf, even if the
    # canonicalization algorithm would add one.
    for x, y in sign_headers + [(x, y.rstrip()) for x, y in cheaders]:
        hasher.update(x)
        hasher.update(b":")
        hasher.update(y)
    return sign_headers


def hash_headers_ed25519(
    pk,
    canonicalize_headers,
    headers,
    include_headers,
    sigheader,
    sig,
):
    """Update hash for signed message header fields."""
    hash_header = ""
    sign_headers = select_headers(headers, include_headers)
    # The call to _remove() assumes that the signature b= only appears
    # once in the signature header
    cheaders = canonicalize_headers.canonicalize_headers(
        [(sigheader[0], RE_BTAG.sub(b"\\1", sigheader[1]))],
    )
    # the dkim sig is hashed with no trailing crlf, even if the
    # canonicalization algorithm would add one.
    for x, y in sign_headers + [(x, y.rstrip()) for x, y in cheaders]:
        hash_header += x + y
    return sign_headers, hash_header


def validate_signature_fields(
    sig,
    mandatory_fields=[b"v", b"a", b"b", b"bh", b"d", b"h", b"s"],
    arc=False,
):
    """Validate DKIM or ARC Signature fields.
    Basic checks for presence and correct formatting of mandatory fields.
    Raises a ValidationError if checks fail, otherwise returns None.
    @param sig: A dict mapping field keys to values.
    @param mandatory_fields: A list of non-optional fields
    @param arc: flag to differentiate between dkim & arc
    """
    if arc:
        hashes = ARC_HASH_ALGORITHMS
    else:
        hashes = HASH_ALGORITHMS
    for field in mandatory_fields:
        if field not in sig:
            raise ValidationError(f"missing {field}=")

    if b"a" in sig and sig[b"a"] not in hashes:
        raise ValidationError(f"unknown signature algorithm: {sig[b'a']}")

    if b"b" in sig:
        if re.match(rb"[\s0-9A-Za-z+/]+=*$", sig[b"b"]) is None:
            raise ValidationError(f"b= value is not valid base64 ({sig[b'b']})")
        if len(re.sub(rb"\s+", b"", sig[b"b"])) % 4 != 0:
            raise ValidationError(f"b= value is not valid base64 ({sig[b'b']})")

    if b"bh" in sig:
        if re.match(rb"[\s0-9A-Za-z+/]+=*$", sig[b"bh"]) is None:
            raise ValidationError(f"bh= value is not valid base64 ({sig[b'bh']})")
        if len(re.sub(rb"\s+", b"", sig[b"bh"])) % 4 != 0:
            raise ValidationError(f"bh= value is not valid base64 ({sig[b'bh']})")

    if b"cv" in sig and sig[b"cv"] not in (CV_Pass, CV_Fail, CV_None):
        raise ValidationError(f"cv= value is not valid ({sig[b'cv']})")

    # Nasty hack to support both str and bytes... check for both the
    # character and integer values.
    if (
        not arc
        and b"i" in sig
        and (
            not sig[b"i"].lower().endswith(sig[b"d"].lower())
            or sig[b"i"][-len(sig[b"d"]) - 1] not in ("@", ".", 64, 46)
        )
    ):
        raise ValidationError(
            f"i= domain is not a subdomain of d= (i={sig[b'i']} d={sig[b'd']})",
        )
    if b"l" in sig and re.match(rb"\d{,76}$", sig[b"l"]) is None:
        raise ValidationError(f"l= value is not a decimal integer ({sig[b'l']})")
    if b"q" in sig and sig[b"q"] != b"dns/txt":
        raise ValidationError(f"q= value is not dns/txt ({sig[b'q']})")

    if b"t" in sig:
        if re.match(rb"\d+$", sig[b"t"]) is None:
            raise ValidationError(f"t= value is not a decimal integer ({sig[b't']})")
        now = int(time.time())
        slop = 36000  # 10H leeway for mailers with inaccurate clocks
        t_sign = int(sig[b"t"])
        if t_sign > now + slop:
            raise ValidationError(f"t= value is in the future ({sig[b't']})")

    if b"v" in sig and sig[b"v"] != b"1":
        raise ValidationError(f"v= value is not 1 ({sig[b'v']})")

    if b"x" in sig:
        if re.match(rb"\d+$", sig[b"x"]) is None:
            raise ValidationError(f"x= value is not a decimal integer ({sig[b'x']})")
        x_sign = int(sig[b"x"])
        now = int(time.time())
        slop = 36000  # 10H leeway for mailers with inaccurate clocks
        if x_sign < now - slop:
            raise ValidationError(f"x= value is past ({sig[b'x']})")
            if x_sign < t_sign:
                raise ValidationError(
                    f"x= value is less than t= value (x={sig[b'x']} t={sig[b't']})",
                )


def rfc822_parse(message):
    """Parse a message in RFC822 format.

    @param message: The message in RFC822 format. Either CRLF or LF is an accepted line separator.
    @return: Returns a tuple of (headers, body) where headers is a list of (name, value) pairs.
    The body is a CRLF-separated string.
    """
    headers = []
    lines = re.split(b"\r?\n", message)
    i = 0
    while i < len(lines):
        if len(lines[i]) == 0:
            # End of headers, return what we have plus the body, excluding the blank line.
            i += 1
            break
        if lines[i][0] in ("\x09", "\x20", 0x09, 0x20):
            headers[-1][1] += lines[i] + b"\r\n"
        else:
            m = re.match(rb"([\x21-\x7e]+?):", lines[i])
            if m is not None:
                headers.append([m.group(1), lines[i][m.end(0) :] + b"\r\n"])
            elif lines[i].startswith(b"From "):
                pass
            else:
                raise MessageFormatError(
                    f"Unexpected characters in RFC822 header: {lines[i]}",
                )
        i += 1
    return (headers, b"\r\n".join(lines[i:]))


def text(s):
    """Normalize bytes/str to str for python 2/3 compatible doctests.
    >>> text(b"foo")
    'foo'
    >>> text("foo")
    'foo'
    >>> text("foo")
    'foo'
    """
    if type(s) is str:
        return s
    s = s.decode("ascii")
    if type(s) is str:
        return s
    return s.encode("ascii")


def fold(header, namelen=0, linesep=b"\r\n"):
    """Fold a header line into multiple crlf-separated lines of text at column
     72.  The crlf does not count for line length.

    >>> text(fold(b"foo"))
    'foo'
    >>> text(fold(b"foo  " + b"foo" * 24).splitlines()[0])
    'foo '
    >>> text(fold(b"foo" * 25).splitlines()[-1])
    ' foo'
    >>> len(fold(b"foo" * 25).splitlines()[0])
    72
    >>> text(fold(b"x"))
    'x'
    >>> text(fold(b"xyz" * 24))
    'xyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyzxyz'
    >>> len(fold(b"xyz" * 48))
    150
    """
    # 72 is the max line length we actually want, but the header field name
    # has to fit in the first line too (See Debian Bug #863690).
    maxleng = 72 - namelen
    if len(header) <= maxleng:
        return header
    if len(header) - header.rfind(b"\r\n") == 2 and len(header) <= maxleng + 2:
        return header
    i = header.rfind(b"\r\n ")
    if i == -1:
        pre = b""
    else:
        i += 3
        pre = header[:i]
        header = header[i:]
    while len(header) > maxleng:
        i = header[:maxleng].rfind(b" ")
        if i == -1:
            j = maxleng
            pre += header[:j] + linesep + b" "
        else:
            j = i + 1
            pre += header[:i] + linesep + b" "
        header = header[j:]
        maxleng = 71
    if len(header) > 2:
        return pre + header
    if pre[0] == b" ":
        return pre[:-1]
    return pre + header


def evaluate_pk(name, s):
    if not s:
        raise KeyFormatError(f"missing public key: {name}")
    try:
        if type(s) is str:
            s = s.encode("ascii")
        pub = parse_tag_value(s)
    except InvalidTagValueList as e:
        raise KeyFormatError(e)
    try:
        if pub[b"v"] != b"DKIM1":
            raise KeyFormatError("bad version")
    except KeyError:
        # Version not required in key record: RFC 6376 3.6.1
        pass
    try:
        if pub[b"k"] == b"ed25519":
            try:
                pk = nacl.signing.VerifyKey(
                    pub[b"p"],
                    encoder=nacl.encoding.Base64Encoder,
                )
            except NameError:
                raise NaClNotFoundError(
                    "pynacl module required for ed25519 signing, see README.md",
                )
            keysize = 256
            ktag = b"ed25519"
    except KeyError:
        pub[b"k"] = b"rsa"
    if pub[b"k"] == b"rsa":
        try:
            pk = parse_public_key(base64.b64decode(pub[b"p"]))
            keysize = bitsize(pk["modulus"])
        except KeyError:
            raise KeyFormatError(f"incomplete public key: {s}")
        except (TypeError, UnparsableKeyError) as e:
            raise KeyFormatError(f"could not parse public key ({pub[b'p']}): {e}")
        ktag = b"rsa"
    if pub[b"k"] != b"rsa" and pub[b"k"] != b"ed25519":
        raise KeyFormatError(f"unknown algorithm in k= tag: {pub[b'k']}")
    seqtlsrpt = False
    try:
        # Ignore unknown service types, RFC 6376 3.6.1
        if pub[b"s"] != b"*" and pub[b"s"] != b"email" and pub[b"s"] != b"tlsrpt":
            pk = None
            keysize = None
            ktag = None
            raise KeyFormatError(f"unknown service type in s= tag: {pub[b's']}")
        if pub[b"s"] == b"tlsrpt":
            seqtlsrpt = True
    except Exception:
        # Default is '*' - all service types, so no error if missing from key record
        pass
    return pk, keysize, ktag, seqtlsrpt


def load_pk_from_dns(name, dnsfunc=get_txt, timeout=5):
    s = dnsfunc(name, timeout=timeout)
    pk, keysize, ktag, seqtlsrpt = evaluate_pk(name, s)
    return pk, keysize, ktag, seqtlsrpt


#: Abstract base class for holding messages and options during DKIM/ARC signing and verification.
class DomainSigner:
    # NOTE - the first 2 indentation levels are 2 instead of 4
    # to minimize changed lines from the function only version.

    #: @param message: an RFC822 formatted message to be signed or verified
    #: (with either \\n or \\r\\n line endings)
    #: @param logger: a logger to which info info will be written (default None)
    #: @param signature_algorithm: the signing algorithm to use when signing
    #: @param info_content: log headers and body after canonicalization (default False)
    #: @param linesep: use this line seperator for folding the headers
    #: @param timeout: number of seconds for DNS lookup timeout (default = 5)
    #: @param tlsrpt: message is an RFC 8460 TLS report (default False)
    #: False: Not a tlsrpt, True: Is a tlsrpt, 'strict': tlsrpt, invalid if
    #: service type is missing. For signing, if True, length is never used.
    def __init__(
        self,
        message=None,
        logger=None,
        signature_algorithm=b"rsa-sha256",
        minkey=1024,
        linesep="\r\n",
        info_content=False,
        timeout=5,
        tlsrpt=False,
        headers=None,
    ):
        if headers:
            b_header = {}

            for h in headers:
                b_header[h.encode("utf-8")] = headers[h][0].encode("utf-8")

            self.headers = b_header
            self.body = b""

            #: The DKIM signing domain last signed or verified.
            self.domain = None
            #: The DKIM key selector last signed or verified.
            self.selector = "default"
            #: Signature parameters of last sign or verify.  To parse
            #: a DKIM-Signature header field that you have in hand,
            #: use L{dkim.util.parse_tag_value}.
            self.signature_fields = {}
            #: The list of headers last signed or verified.  Each header
            #: is a name,value tuple.  FIXME: The headers are canonicalized.
            #: This could be more useful as original headers.
            self.signed_headers = []
            #: The public key size last verified.
            self.keysize = 0
        else:
            self.set_message(message)

        if logger is None:
            logger = logging.getLogger(__name__)

        self.logger = logger
        self.info_content = (
            info_content and logger is not None and logger.isEnabledFor(logging.info)
        )
        if signature_algorithm not in HASH_ALGORITHMS:
            raise ParameterError(
                "Unsupported signature algorithm: " + signature_algorithm,
            )
        self.signature_algorithm = signature_algorithm
        #: Header fields which should be signed.  Default as suggested by RFC6376
        self.should_sign = set(DKIM.SHOULD)
        #: Header fields which should not be signed.  The default is from RFC6376.
        #: Attempting to sign these headers results in an exception.
        #: If it is necessary to sign one of these, it must be removed
        #: from this list first.
        self.should_not_sign = set(DKIM.SHOULD_NOT)
        #: Header fields to sign an extra time to prevent additions.
        self.frozen_sign = set(DKIM.FROZEN)
        #: Minimum public key size.  Shorter keys raise KeyFormatError. The
        #: default is 1024
        self.minkey = minkey
        # use this line seperator for output
        self.linesep = linesep
        self.timeout = timeout
        self.tlsrpt = tlsrpt
        # Service type in DKIM record is s=tlsrpt
        self.seqtlsrpt = False

    #: Header fields to protect from additions by default.
    #:
    #: The short list below is the result more of instinct than logic.
    #: @since: 0.5
    FROZEN = (b"from",)

    #: The rfc6376 recommended header fields to sign
    #: @since: 0.5
    SHOULD = (
        b"from",
        b"sender",
        b"reply-to",
        b"subject",
        b"date",
        b"message-id",
        b"to",
        b"cc",
        b"mime-version",
        b"content-type",
        b"content-transfer-encoding",
        b"content-id",
        b"content-description",
        b"resent-date",
        b"resent-from",
        b"resent-sender",
        b"resent-to",
        b"resent-cc",
        b"resent-message-id",
        b"in-reply-to",
        b"references",
        b"list-id",
        b"list-help",
        b"list-unsubscribe",
        b"list-subscribe",
        b"list-post",
        b"list-owner",
        b"list-archive",
    )

    #: The rfc6376 recommended header fields not to sign.
    #: @since: 0.5
    SHOULD_NOT = (
        b"return-path",
        b"received",
        b"comments",
        b"keywords",
        b"bcc",
        b"resent-bcc",
        b"dkim-signature",
    )

    # Doesn't seem to be used (GS)
    #: The U{RFC5322<http://tools.ietf.org/html/rfc5322#section-3.6>}
    #: complete list of singleton headers (which should
    #: appear at most once).  This can be used for a "paranoid" or
    #: "strict" signing mode.
    #: Bcc in this list is in the SHOULD NOT sign list, the rest could
    #: be in the default FROZEN list, but that could also make signatures
    #: more fragile than necessary.
    #: @since: 0.5
    RFC5322_SINGLETON = (
        b"date",
        b"from",
        b"sender",
        b"reply-to",
        b"to",
        b"cc",
        b"bcc",
        b"message-id",
        b"in-reply-to",
        b"references",
    )

    def add_frozen(self, s):
        """Add headers not in should_not_sign to frozen_sign.
        @param s: list of headers to add to frozen_sign
        @since: 0.5

        >>> dkim = DKIM()
        >>> dkim.add_frozen(DKIM.RFC5322_SINGLETON)
        >>> [text(x) for x in sorted(dkim.frozen_sign)]
        [
            'cc', 'date', 'from', 'in-reply-to', 'message-id', 'references',
            'reply-to', 'sender', 'to'
        ]
        >>> dkim2 = DKIM()
        >>> dkim2.add_frozen((b"date", b"subject"))
        >>> [text(x) for x in sorted(dkim2.frozen_sign)]
        ['date', 'from', 'subject']
        """
        self.frozen_sign.update(
            x.lower() for x in s if x.lower() not in self.should_not_sign
        )

    def add_should_not(self, s):
        """Add headers not in should_not_sign to frozen_sign.
        @param s: list of headers to add to frozen_sign
        @since: 0.9

        >>> dkim = DKIM()
        >>> dkim.add_should_not(DKIM.RFC5322_SINGLETON)
        >>> [text(x) for x in sorted(dkim.should_not_sign)]
        [
            'bcc', 'cc', 'comments', 'date', 'dkim-signature', 'in-reply-to',
            'keywords', 'message-id', 'received', 'references', 'reply-to',
            'resent-bcc', 'return-path', 'sender', 'to'
        ]
        """
        self.should_not_sign.update(
            x.lower() for x in s if x.lower() not in self.frozen_sign
        )

    #: Load a new message to be signed or verified.
    #: @param message: an RFC822 formatted message to be signed or verified
    #: (with either \\n or \\r\\n line endings)
    #: @since: 0.5
    def set_message(self, message):
        if message:
            self.headers, self.body = rfc822_parse(message)
        else:
            self.headers, self.body = [], ""
        #: The DKIM signing domain last signed or verified.
        self.domain = None
        #: The DKIM key selector last signed or verified.
        self.selector = "default"
        #: Signature parameters of last sign or verify.  To parse
        #: a DKIM-Signature header field that you have in hand,
        #: use L{dkim.util.parse_tag_value}.
        self.signature_fields = {}
        #: The list of headers last signed or verified.  Each header
        #: is a name,value tuple.  FIXME: The headers are canonicalized.
        #: This could be more useful as original headers.
        self.signed_headers = []
        #: The public key size last verified.
        self.keysize = 0

    def default_sign_headers(self):
        """Return the default list of headers to sign: those in should_sign or
        frozen_sign, with those in frozen_sign signed an extra time to prevent
        additions.
        @since: 0.5
        """
        hset = self.should_sign | self.frozen_sign
        include_headers = [x for x, y in self.headers if x.lower() in hset]
        return include_headers + [
            x for x in include_headers if x.lower() in self.frozen_sign
        ]

    def all_sign_headers(self):
        """Return header list of all existing headers not in should_not_sign.
        @since: 0.5
        """
        return [x for x, y in self.headers if x.lower() not in self.should_not_sign]

    # Abstract helper method to generate a tag=value header from a list of fields
    #: @param fields: A list of key value tuples to be included in the header
    #: @param include_headers: A list message headers to include in the b= signature computation
    #: @param canon_policy: A canonicialization policy for b= & bh=
    #: @param header_name: The name of the generated header
    #: @param pk: The private key used for signature generation
    #: @param standardize:  Flag to enable 'standard' header syntax
    def gen_header(
        self,
        fields,
        include_headers,
        canon_policy,
        header_name,
        pk,
        standardize=False,
    ):
        if standardize:
            lower = [
                (x, y.lower().replace(b" ", b"")) for (x, y) in fields if x != b"bh"
            ]
            reg = [(x, y.replace(b" ", b"")) for (x, y) in fields if x == b"bh"]
            fields = lower + reg
            fields = sorted(fields, key=(lambda x: x[0]))

        header_value = b"; ".join(b"=".join(x) for x in fields)
        if not standardize:
            header_value = fold(header_value, namelen=len(header_name), linesep=b"\r\n")
        header_value = RE_BTAG.sub(b"\\1", header_value)
        header = (header_name, b" " + header_value)
        h = HashThrough(self.hasher(), self.info_content)
        sig = dict(fields)

        headers = canon_policy.canonicalize_headers(self.headers)
        self.signed_headers = hash_headers(
            h,
            canon_policy,
            headers,
            include_headers,
            header,
            sig,
        )
        if self.info_content:
            self.logger.info("sign %s headers: %r" % (header_name, h.hashed()))

        if (
            self.signature_algorithm == b"rsa-sha256"
            or self.signature_algorithm == b"rsa-sha1"
        ):
            try:
                sig2 = RSASSA_PKCS1_v1_5_sign(h, pk)
            except DigestTooLargeError:
                raise ParameterError("digest too large for modulus")
        elif self.signature_algorithm == b"ed25519-sha256":
            sigobj = pk.sign(h.digest())
            sig2 = sigobj.signature
        # Folding b= is explicity allowed, but yahoo and live.com are broken
        # header_value += base64.b64encode(bytes(sig2))
        # Instead of leaving unfolded (which lets an MTA fold it later and still
        # breaks yahoo and live.com), we change the default signing mode to
        # relaxed/simple (for broken receivers), and fold now.
        idx = [i for i in range(len(fields)) if fields[i][0] == b"b"][0]
        fields[idx] = (b"b", base64.b64encode(bytes(sig2)))
        header_value = b"; ".join(b"=".join(x) for x in fields) + self.linesep

        if not standardize:
            header_value = fold(
                header_value,
                namelen=len(header_name),
                linesep=self.linesep,
            )

        return header_value

    def verify_sig_process(self, sig, include_headers, sig_header, dnsfunc):
        """Non-async sensitive verify_sig elements.  Separated to avoid async code
        duplication.
        """
        # RFC 8460 MAY ignore signatures without tlsrpt Service Type
        if self.tlsrpt == "strict" and not self.seqtlsrpt:
            raise ValidationError("Message is tlsrpt and Service Type is not tlsrpt")
        # Inferred requirement from both RFC 8460 and RFC 6376
        if not self.tlsrpt and self.seqtlsrpt:
            raise ValidationError("Message is not tlsrpt and Service Type is tlsrpt")

        try:
            canon_policy = CanonicalizationPolicy.from_c_value(
                sig.get(b"c", b"simple/simple"),
            )
        except InvalidCanonicalizationPolicyError as e:
            raise MessageFormatError(f"invalid c= value: {e.args[0]}")

        hasher = HASH_ALGORITHMS[sig[b"a"]]

        # address bug#644046 by including any additional From header
        # fields when verifying.  Since there should be only one From header,
        # this shouldn't break any legitimate messages.  This could be
        # generalized to check for extras of other singleton headers.
        if b"from" in include_headers:
            include_headers.append(b"from")
        h = HashThrough(hasher(), self.info_content)

        headers = canon_policy.canonicalize_headers(self.headers)
        self.signed_headers = hash_headers(
            h,
            canon_policy,
            headers,
            include_headers,
            sig_header,
            sig,
        )
        if self.info_content:
            self.logger.info(
                "signed for %s: %r" % (sig_header[b"dkim-signature"], h.hashed()),
            )
        signature = base64.b64decode(re.sub(rb"\s+", b"", sig[b"b"]))
        if self.ktag == b"rsa":
            try:
                res = RSASSA_PKCS1_v1_5_verify(h, signature, self.pk)
                self.logger.info(f"{sig_header[b'dkim-signature']} valid: {res}")
                if res and self.keysize < self.minkey:
                    raise KeyFormatError("public key too small: %d" % self.keysize)
                return res
            except (TypeError, DigestTooLargeError) as e:
                raise KeyFormatError(f"digest too large for modulus: {e}")
        elif self.ktag == b"ed25519":
            try:
                self.pk.verify(h.digest(), signature)
                self.logger.info(f"{(sig_header[0])} valid")
                return True
            except nacl.exceptions.BadSignatureError:
                return False
        else:
            raise UnknownKeyTypeError(self.ktag)

    # Abstract helper method to verify a signed header
    #: @param sig: List of (key, value) tuples containing tag=values of the header
    #: @param include_headers: headers to validate b= signature against
    #: @param sig_header: (header_name, header_value)
    #: @param dnsfunc: interface to dns
    def verify_sig(self, sig, include_headers, sig_header, dnsfunc):
        name = sig[b"s"] + b"._domainkey." + sig[b"d"] + b"."
        try:
            self.pk, self.keysize, self.ktag, self.seqtlsrpt = load_pk_from_dns(
                name,
                dnsfunc,
                timeout=self.timeout,
            )
        except KeyFormatError as e:
            self.logger.error(f"{e}")
            return False
        except binascii.Error as e:
            self.logger.error(f"KeyFormatError: {e}")
            return False
        return self.verify_sig_process(sig, include_headers, sig_header, dnsfunc)


class DKIM(DomainSigner):
    #: Sign an RFC822 message and return the DKIM-Signature header line.
    #:
    #: The include_headers option gives full control over which header fields
    #: are signed.  Note that signing a header field that doesn't exist prevents
    #: that field from being added without breaking the signature.  Repeated
    #: fields (such as Received) can be signed multiple times.  Instances
    #: of the field are signed from bottom to top.  Signing a header field more
    #: times than are currently present prevents additional instances
    #: from being added without breaking the signature.
    #:
    #: The length option allows the message body to be appended to by MTAs
    #: enroute (e.g. mailing lists that append unsubscribe information)
    #: without breaking the signature.
    #:
    #: The default include_headers for this method differs from the backward
    #: compatible sign function, which signs all headers not
    #: in should_not_sign.  The default list for this method can be modified
    #: by tweaking should_sign and frozen_sign (or even should_not_sign).
    #: It is only necessary to pass an include_headers list when precise control
    #: is needed.
    #:
    #: @param selector: the DKIM selector value for the signature
    #: @param domain: the DKIM domain value for the signature
    #: @param privkey: a PKCS#1 private key in base64-encoded text form
    #: @param identity: the DKIM identity value for the signature
    #: (default "@"+domain)
    #: @param canonicalize: the canonicalization algorithms to use
    #: (default (Simple, Simple))
    #: @param include_headers: a list of strings indicating which headers
    #: are to be signed (default rfc4871 recommended headers)
    #: @param length: true if the l= tag should be included to indicate
    #: body length signed (default False).
    #: @return: DKIM-Signature header field terminated by '\r\n'
    #: @raise DKIMException: when the message, include_headers, or key are badly
    #: formed.
    def sign(
        self,
        selector,
        domain,
        privkey,
        signature_algorithm=None,
        identity=None,
        canonicalize=(b"relaxed", b"simple"),
        include_headers=None,
        length=False,
    ):
        if signature_algorithm:
            self.signature_algorithm = signature_algorithm
        if (
            self.signature_algorithm == b"rsa-sha256"
            or self.signature_algorithm == b"rsa-sha1"
        ):
            try:
                pk = parse_pem_private_key(privkey)
            except UnparsableKeyError as e:
                raise KeyFormatError(str(e))
        elif self.signature_algorithm == b"ed25519-sha256":
            try:
                pk = nacl.signing.SigningKey(
                    privkey,
                    encoder=nacl.encoding.Base64Encoder,
                )
            except NameError:
                raise NaClNotFoundError(
                    "pynacl module required for ed25519 signing, see README.md",
                )

        if identity is not None and not identity.endswith(domain):
            raise ParameterError("identity must end with domain")

        canon_policy = CanonicalizationPolicy.from_c_value(b"/".join(canonicalize))

        if include_headers is None:
            include_headers = self.default_sign_headers()
        try:
            include_headers = [bytes(x, "utf-8") for x in include_headers]
        except TypeError:
            # TypeError means it's already bytes and we're good or we're in
            # Python 2 and we don't care.  See LP: #1776775.
            pass

        include_headers = tuple([x.lower() for x in include_headers])
        # record what verify should extract
        self.include_headers = include_headers

        if self.tlsrpt:
            # RFC 8460 MUST NOT
            length = False

        # rfc4871 says FROM is required
        if b"from" not in include_headers:
            raise ParameterError("The From header field MUST be signed")

        # raise exception for any SHOULD_NOT headers, call can modify
        # SHOULD_NOT if really needed.
        for x in set(include_headers).intersection(self.should_not_sign):
            raise ParameterError(f"The {x} header field SHOULD NOT be signed")

        body = canon_policy.canonicalize_body(self.body)

        self.hasher = HASH_ALGORITHMS[self.signature_algorithm]
        h = self.hasher()
        h.update(body)
        bodyhash = base64.b64encode(h.digest())

        sigfields = [
            x
            for x in [
                (b"v", b"1"),
                (b"a", self.signature_algorithm),
                (b"c", canon_policy.to_c_value()),
                (b"d", domain),
                (b"i", identity or b"@" + domain),
                length and (b"l", str(len(body)).encode("ascii")),
                (b"q", b"dns/txt"),
                (b"s", selector),
                (b"t", str(int(time.time())).encode("ascii")),
                (b"h", b" : ".join(include_headers)),
                (b"bh", bodyhash),
                # Force b= to fold onto it's own line so that refolding after
                # adding sig doesn't change whitespace for previous tags.
                (b"b", b"0" * 60),
            ]
            if x
        ]

        res = self.gen_header(
            sigfields,
            include_headers,
            canon_policy,
            b"DKIM-Signature",
            pk,
        )

        self.domain = domain
        self.selector = selector
        self.signature_fields = dict(sigfields)
        return b"DKIM-Signature: " + res

    #: Checks if any DKIM signature is present
    #: @return: True if there is one or more DKIM signatures present or False otherwise
    def present(self):
        return (
            len([(x, y) for x, y in self.headers if x.lower() == b"dkim-signature"]) > 0
        )

    def verify_headerprep(self, idx=0):
        """Non-DNS verify parts to minimize asyncio code duplication."""
        # sigheaders = [
        #   (x.encode('utf-8'),self.headers[x][0].encode('utf-8')) for x in self.headers
        #   if x.lower() == "dkim-signature"
        # ]
        sigheaders = []
        for x in self.headers:
            if x.lower() == b"dkim-signature":
                dkim_sig = {}
                dkim_sig[x] = self.headers[x]
                sigheaders.append(dkim_sig)
                # sigheaders[x] = self.headers[x]
        # sigheaders = {(x,self.headers[x]) for x in self.headers if x.lower() == b"dkim-signature"}

        # sigheaders = [(x,y) for x,y in self.headers if x.lower() == b"dkim-signature"]
        if len(sigheaders) <= idx:
            return False

        # By default, we validate the first DKIM-Signature line found.
        try:
            sig = parse_tag_value(sigheaders[idx][b"dkim-signature"])
            self.signature_fields = sig
        except InvalidTagValueList as e:
            raise MessageFormatError(e)

        validate_signature_fields(sig)
        self.domain = sig[b"d"]
        self.selector = sig[b"s"]

        include_headers = [x.lower() for x in re.split(rb"\s*:\s*", sig[b"h"])]
        self.include_headers = tuple(include_headers)
        return sig, include_headers, sigheaders

    #: Verify a DKIM signature.
    #: @type idx: int
    #: @param idx: which signature to verify.  The first (topmost) signature is 0.
    #: @type dnsfunc: callable
    #: @param dnsfunc: an option function to lookup TXT resource records
    #: for a DNS domain.  The default uses dnspython or pydns.
    #: @return: True if signature verifies or False otherwise
    #: @raise DKIMException: when the message, signature, or key are badly formed
    def verify(self, idx=0, dnsfunc=get_txt):
        prep = self.verify_headerprep(idx)
        if prep:
            sig, include_headers, sigheaders = prep
            return self.verify_sig(sig, include_headers, sigheaders[idx], dnsfunc)
        return False  # No signature


#: Hold messages and options during ARC signing and verification.
class ARC(DomainSigner):
    #: Header fields used by ARC
    ARC_HEADERS = (b"arc-seal", b"arc-message-signature", b"arc-authentication-results")

    #: Regex to extract i= value from ARC headers
    INSTANCE_RE = re.compile(rb"[\s;]?i\s*=\s*(\d+)", re.MULTILINE | re.IGNORECASE)

    def sorted_arc_headers(self):
        headers = []
        # Use relaxed canonicalization to unfold and clean up headers
        relaxed_headers = Relaxed.canonicalize_headers(self.headers)
        for x, y in relaxed_headers:
            if x.lower() in ARC.ARC_HEADERS:
                m = ARC.INSTANCE_RE.search(y)
                if m is not None:
                    try:
                        i = int(m.group(1))
                        headers.append((i, (x, y)))
                    except ValueError:
                        self.logger.info(
                            f"invalid instance number {m.group(1)}: '{x}: {y}'",
                        )
                else:
                    self.logger.info(f"not instance number: '{x}: {y}'")

        if len(headers) == 0:
            return 0, []

        def arc_header_key(a):
            return [a[0], a[1][0].lower(), a[1][1].lower()]

        headers = sorted(headers, key=arc_header_key)
        headers.reverse()
        return headers[0][0], headers

    #: Sign an RFC822 message and return the list of ARC set header lines
    #:
    #: The include_headers option gives full control over which header fields
    #: are signed for the ARC-Message-Signature.  Note that signing a header
    #: field that doesn't exist prevents
    #: that field from being added without breaking the signature.  Repeated
    #: fields (such as Received) can be signed multiple times.  Instances
    #: of the field are signed from bottom to top.  Signing a header field more
    #: times than are currently present prevents additional instances
    #: from being added without breaking the signature.
    #:
    #: The default include_headers for this method differs from the backward
    #: compatible sign function, which signs all headers not
    #: in should_not_sign.  The default list for this method can be modified
    #: by tweaking should_sign and frozen_sign (or even should_not_sign).
    #: It is only necessary to pass an include_headers list when precise control
    #: is needed.
    #:
    #: @param selector: the DKIM selector value for the signature
    #: @param domain: the DKIM domain value for the signature
    #: @param privkey: a PKCS#1 private key in base64-encoded text form
    #: @param srv_id: a srv_id for identifying AR headers to sign & extract cv from
    #: @param include_headers: a list of strings indicating which headers
    #: are to be signed (default rfc4871 recommended headers)
    #: @return: list of ARC set header fields
    #: @raise DKIMException: when the message, include_headers, or key are badly
    #: formed.
    def sign(
        self,
        selector,
        domain,
        privkey,
        srv_id,
        include_headers=None,
        timestamp=None,
        standardize=False,
    ):
        INSTANCE_LIMIT = 50  # Maximum allowed i= value
        self.add_should_not(("Authentication-Results",))
        # check if authres has been imported
        try:
            AuthenticationResultsHeader
        except Exception:
            self.logger.info("authres package not installed")
            raise AuthresNotFoundError

        try:
            pk = parse_pem_private_key(privkey)
        except UnparsableKeyError as e:
            raise KeyFormatError(str(e))

        # extract, parse, filter & group AR headers
        ar_headers = [
            res.strip() for [ar, res] in self.headers if ar == b"Authentication-Results"
        ]
        grouped_headers = [
            (
                res,
                AuthenticationResultsHeader.parse(
                    "Authentication-Results: " + res.decode("utf-8"),
                ),
            )
            for res in ar_headers
        ]
        auth_headers = [
            res
            for res in grouped_headers
            if res[1].authserv_id == srv_id.decode("utf-8")
        ]

        if len(auth_headers) == 0:
            self.logger.info("no AR headers found, chain terminated")
            return []

        # consolidate headers
        results_lists = [
            raw.replace(srv_id + b";", b"").strip() for (raw, parsed) in auth_headers
        ]
        results_lists = [tags.split(b";") for tags in results_lists]
        results = [tag.strip() for sublist in results_lists for tag in sublist]
        auth_results = srv_id + b"; " + (b";" + self.linesep + b"  ").join(results)

        # extract cv
        parsed_auth_results = AuthenticationResultsHeader.parse(
            "Authentication-Results: " + auth_results.decode("utf-8"),
        )
        arc_results = [
            res for res in parsed_auth_results.results if res.method == "arc"
        ]
        if len(arc_results) == 0:
            chain_validation_status = CV_None
        elif len(arc_results) != 1:
            self.logger.info("multiple AR arc stamps found, failing chain")
            chain_validation_status = CV_Fail
        else:
            chain_validation_status = arc_results[0].result.lower().encode("utf-8")

        # Setup headers
        if include_headers is None:
            include_headers = self.default_sign_headers()

        include_headers = tuple([x.lower() for x in include_headers])

        # record what verify should extract
        self.include_headers = include_headers

        # rfc4871 says FROM is required
        if b"from" not in include_headers:
            raise ParameterError("The From header field MUST be signed")

        # raise exception for any SHOULD_NOT headers, call can modify
        # SHOULD_NOT if really needed.
        for x in set(include_headers).intersection(self.should_not_sign):
            raise ParameterError(f"The {x} header field SHOULD NOT be signed")

        max_instance, arc_headers_w_instance = self.sorted_arc_headers()
        instance = 1
        if len(arc_headers_w_instance) != 0:
            instance = max_instance + 1
        if instance > INSTANCE_LIMIT:
            raise ParameterError("Maximum instance tag value exceeded")

        if instance == 1 and chain_validation_status != CV_None:
            raise ParameterError(
                "No existing chain found on message, cv should be none",
            )
        if instance != 1 and chain_validation_status == CV_None:
            self.logger.info(
                "no previous AR arc results found and instance > 1, chain terminated",
            )
            return []

        new_arc_set = []
        if chain_validation_status != CV_Fail:
            arc_headers = [y for x, y in arc_headers_w_instance]
        else:  # don't include previous sets for a failed/invalid chain
            arc_headers = []

        # Compute ARC-Authentication-Results
        aar_value = ("i=%d; " % instance).encode("utf-8") + auth_results
        if aar_value[-1] != b"\n":
            aar_value += b"\r\n"

        new_arc_set.append(b"ARC-Authentication-Results: " + aar_value)
        self.headers.insert(0, (b"arc-authentication-results", aar_value))
        arc_headers.insert(0, (b"ARC-Authentication-Results", aar_value))

        # Compute bh=
        canon_policy = CanonicalizationPolicy.from_c_value(b"relaxed/relaxed")

        self.hasher = HASH_ALGORITHMS[self.signature_algorithm]
        h = HashThrough(self.hasher(), self.info_content)
        h.update(canon_policy.canonicalize_body(self.body))
        if self.info_content:
            self.logger.info("sign ams body hashed: %r" % h.hashed())
        bodyhash = base64.b64encode(h.digest())

        # Compute ARC-Message-Signature
        timestamp = str(timestamp or int(time.time())).encode("ascii")
        ams_fields = [
            x
            for x in [
                (b"i", str(instance).encode("ascii")),
                (b"a", self.signature_algorithm),
                (b"c", b"relaxed/relaxed"),
                (b"d", domain),
                (b"s", selector),
                (b"t", timestamp),
                (b"h", b" : ".join(include_headers)),
                (b"bh", bodyhash),
                # Force b= to fold onto it's own line so that refolding after
                # adding sig doesn't change whitespace for previous tags.
                (b"b", b"0" * 60),
            ]
            if x
        ]

        res = self.gen_header(
            ams_fields,
            include_headers,
            canon_policy,
            b"ARC-Message-Signature",
            pk,
            standardize,
        )

        new_arc_set.append(b"ARC-Message-Signature: " + res)
        self.headers.insert(0, (b"ARC-Message-Signature", res))
        arc_headers.insert(0, (b"ARC-Message-Signature", res))

        # Compute ARC-Seal
        as_fields = [
            x
            for x in [
                (b"i", str(instance).encode("ascii")),
                (b"cv", chain_validation_status),
                (b"a", self.signature_algorithm),
                (b"d", domain),
                (b"s", selector),
                (b"t", timestamp),
                # Force b= to fold onto it's own line so that refolding after
                # adding sig doesn't change whitespace for previous tags.
                (b"b", b"0" * 60),
            ]
            if x
        ]

        as_include_headers = [x[0].lower() for x in arc_headers]
        as_include_headers.reverse()

        # if our chain is failing or invalid, we only grab the most recent set
        # reversing the order of the headers accomplishes this
        if chain_validation_status == CV_Fail:
            self.headers.reverse()
        if b"h" in as_fields:
            raise ValidationError("h= tag not permitted in ARC-Seal header field")
        res = self.gen_header(
            as_fields,
            as_include_headers,
            canon_policy,
            b"ARC-Seal",
            pk,
            standardize,
        )

        new_arc_set.append(b"ARC-Seal: " + res)
        self.headers.insert(0, (b"ARC-Seal", res))
        arc_headers.insert(0, (b"ARC-Seal", res))

        new_arc_set.reverse()

        return new_arc_set

    #: Verify an ARC set.
    #: @type instance: int
    #: @param instance: which ARC set to verify, based on i= instance.
    #: @type dnsfunc: callable
    #: @param dnsfunc: an optional function to lookup TXT resource records
    #: for a DNS domain.  The default uses dnspython or pydns.
    #: @return: True if signature verifies or False otherwise
    #: @return: three-tuple of (CV Result (CV_Pass, CV_Fail, CV_None or None, for a
    # chain that has ended), list of
    #: result dictionaries, result reason)
    #: @raise DKIMException: when the message, signature, or key are badly formed
    def verify(self, dnsfunc=get_txt):
        result_data = []
        max_instance, arc_headers_w_instance = self.sorted_arc_headers()
        if max_instance == 0:
            return CV_None, result_data, "Message is not ARC signed"
        for instance in range(max_instance, 0, -1):
            try:
                result = self.verify_instance(
                    arc_headers_w_instance,
                    instance,
                    dnsfunc=dnsfunc,
                )
                result_data.append(result)
            except DKIMException as e:
                self.logger.error(f"{e}")
                return CV_Fail, result_data, f"{e}"

        # Most recent instance must ams-validate
        if not result_data[0]["ams-valid"]:
            return (
                CV_Fail,
                result_data,
                "Most recent ARC-Message-Signature did not validate",
            )
        for result in result_data:
            if result["cv"] == CV_Fail:
                return (
                    None,
                    result_data,
                    "ARC-Seal[%d] reported failure, the chain is terminated"
                    % result["instance"],
                )
            if not result["as-valid"]:
                return (
                    CV_Fail,
                    result_data,
                    "ARC-Seal[%d] did not validate" % result["instance"],
                )
            if ((result["instance"] == 1) and (result["cv"] != CV_None)) or (
                (result["instance"] != 1) and (result["cv"] == CV_None)
            ):
                return (
                    CV_Fail,
                    result_data,
                    "ARC-Seal[%d] reported invalid status %s"
                    % (result["instance"], result["cv"]),
                )
        return CV_Pass, result_data, "success"

    #: Verify an ARC set.
    #: @type arc_headers_w_instance: list
    #: @param arc_headers_w_instance: list of tuples, (instance, (name, value)) of
    #: ARC headers
    #: @type instance: int
    #: @param instance: which ARC set to verify, based on i= instance.
    #: @type dnsfunc: callable
    #: @param dnsfunc: an optional function to lookup TXT resource records
    #: for a DNS domain.  The default uses dnspython or pydns.
    #: @return: True if signature verifies or False otherwise
    #: @raise DKIMException: when the message, signature, or key are badly formed
    def verify_instance(self, arc_headers_w_instance, instance, dnsfunc=get_txt):
        if (instance == 0) or (len(arc_headers_w_instance) == 0):
            raise ParameterError(
                "request to verify instance %d not present" % (instance),
            )

        aar_value = None
        ams_value = None
        as_value = None
        arc_headers = []
        output = {"instance": instance}

        for i, arc_header in arc_headers_w_instance:
            if i > instance:
                continue
            arc_headers.append(arc_header)
            if i == instance:
                if arc_header[0].lower() == b"arc-authentication-results":
                    if aar_value is not None:
                        raise MessageFormatError(
                            "Duplicate ARC-Authentication-Results for instance %d"
                            % instance,
                        )
                    aar_value = arc_header[1]
                elif arc_header[0].lower() == b"arc-message-signature":
                    if ams_value is not None:
                        raise MessageFormatError(
                            "Duplicate ARC-Message-Signature for instance %d"
                            % instance,
                        )
                    ams_value = arc_header[1]
                elif arc_header[0].lower() == b"arc-seal":
                    if as_value is not None:
                        raise MessageFormatError(
                            "Duplicate ARC-Seal for instance %d" % instance,
                        )
                    as_value = arc_header[1]

        if (aar_value is None) or (ams_value is None) or (as_value is None):
            raise MessageFormatError("Incomplete ARC set for instance %d" % instance)

        output["aar-value"] = aar_value

        # Validate Arc-Message-Signature
        try:
            sig = parse_tag_value(ams_value)
        except InvalidTagValueList as e:
            raise MessageFormatError(e)

        self.logger.info("ams sig[%d]: %r" % (instance, sig))

        validate_signature_fields(
            sig,
            [b"i", b"a", b"b", b"bh", b"d", b"h", b"s"],
            True,
        )
        output["ams-domain"] = sig[b"d"]
        output["ams-selector"] = sig[b"s"]

        include_headers = [x.lower() for x in re.split(rb"\s*:\s*", sig[b"h"])]
        if b"arc-seal" in include_headers:
            raise ParameterError("The Arc-Message-Signature MUST NOT sign ARC-Seal")

        # we can't use the AMS provided above, as it's already been canonicalized
        # relaxed
        # for use in validating the AS.  However the AMS is included in the AMS itself,
        # and this can use simple canonicalization

        # raw_ams_header = [
        #     (x, y) for (x, y) in self.headers
        #     if x.lower() == b'arc-message-signature'
        # ][0]
        raw_ams_header = [
            (x, self.headers[x])
            for x in self.headers
            if x.lower() == b"arc-message-signature"
        ][0]

        # Only relaxed canonicalization used by ARC
        if b"c" not in sig:
            sig[b"c"] = b"relaxed/relaxed"
        try:
            ams_valid = self.verify_sig(sig, include_headers, raw_ams_header, dnsfunc)
        except DKIMException as e:
            self.logger.error(f"{e}")
            ams_valid = False

        output["ams-valid"] = ams_valid
        self.logger.info("ams valid: %r" % ams_valid)

        # Validate Arc-Seal
        try:
            sig = parse_tag_value(as_value)
        except InvalidTagValueList as e:
            raise MessageFormatError(e)

        self.logger.info("as sig[%d]: %r" % (instance, sig))

        validate_signature_fields(sig, [b"i", b"a", b"b", b"cv", b"d", b"s"], True)
        if b"h" in sig:
            raise ValidationError("h= tag not permitted in ARC-Seal header field")

        output["as-domain"] = sig[b"d"]
        output["as-selector"] = sig[b"s"]
        output["cv"] = sig[b"cv"]

        as_include_headers = [x[0].lower() for x in arc_headers]
        as_include_headers.reverse()
        as_header = (b"ARC-Seal", b" " + as_value)
        # Only relaxed canonicalization used by ARC
        if b"c" not in sig:
            sig[b"c"] = b"relaxed/relaxed"
        try:
            as_valid = self.verify_sig(sig, as_include_headers[:-1], as_header, dnsfunc)
        except DKIMException as e:
            self.logger.error(f"{e}")
            as_valid = False

        output["as-valid"] = as_valid
        self.logger.info("as valid: %r" % as_valid)
        return output


def sign(
    message,
    selector,
    domain,
    privkey,
    identity=None,
    canonicalize=(b"relaxed", b"simple"),
    signature_algorithm=b"rsa-sha256",
    include_headers=None,
    length=False,
    logger=None,
    linesep=b"\r\n",
    tlsrpt=False,
):
    # type: (bytes, bytes, bytes, bytes, bytes, tuple, bytes, list, bool, any) -> bytes
    """Sign an RFC822 message and return the DKIM-Signature header line.
    @param message: an RFC822 formatted message (with either \\n or \\r\\n line endings)
    @param selector: the DKIM selector value for the signature
    @param domain: the DKIM domain value for the signature
    @param privkey: a PKCS#1 private key in base64-encoded text form
    @param identity: the DKIM identity value for the signature (default "@"+domain)
    @param canonicalize: the canonicalization algorithms to use
        (default (Simple, Simple))
    @param signature_algorithm: the signing algorithm to use when signing
    @param include_headers: a list of strings indicating which headers are to be signed
        (default all headers not listed as SHOULD NOT sign)
    @param length: true if the l= tag should be included to indicate body length
        (default False)
    @param logger: a logger to which info info will be written (default None)
    @param linesep: use this line seperator for folding the headers
    @param tlsrpt: message is an RFC 8460 TLS report (default False)
     False: Not a tlsrpt, True: Is a tlsrpt, 'strict': tlsrpt, invalid if
     service type is missing. For signing, if True, length is never used.
    @return: DKIM-Signature header field terminated by \\r\\n
    @raise DKIMException: when the message, include_headers, or key are badly formed.
    """
    d = DKIM(
        message,
        logger=logger,
        signature_algorithm=signature_algorithm,
        linesep=linesep,
        tlsrpt=tlsrpt,
    )
    return d.sign(
        selector,
        domain,
        privkey,
        identity=identity,
        canonicalize=canonicalize,
        include_headers=include_headers,
        length=length,
    )


def verify(message, logger=None, dnsfunc=get_txt, minkey=1024, timeout=5, tlsrpt=False):
    """Verify the first (topmost) DKIM signature on an RFC822 formatted message.
    @param message: an RFC822 formatted message (with either \\n or \\r\\n line endings)
    @param logger: a logger to which info info will be written (default None)
    @param timeout: number of seconds for DNS lookup timeout (default = 5)
    @param tlsrpt: message is an RFC 8460 TLS report (default False)
     False: Not a tlsrpt, True: Is a tlsrpt, 'strict': tlsrpt, invalid if
     service type is missing. For signing, if True, length is never used.
    @return: True if signature verifies or False otherwise
    """
    # type: (bytes, any, function, int) -> bool
    d = DKIM(message, logger=logger, minkey=minkey, timeout=timeout, tlsrpt=tlsrpt)
    try:
        return d.verify(dnsfunc=dnsfunc)
    except DKIMException as x:
        if logger is not None:
            logger.error(f"{x}")
        return False


# aiodns requires Python 3.5+, so no async before that
if sys.version_info >= (3, 5):
    try:
        from dkim.asyncsupport import verify_async

        dkim_verify_async = verify_async
    except ImportError:
        # If aiodns is not installed, then async verification is not available
        pass

# For consistency with ARC
dkim_sign = sign
dkim_verify = verify


def arc_sign(
    message,
    selector,
    domain,
    privkey,
    srv_id,
    signature_algorithm=b"rsa-sha256",
    include_headers=None,
    timestamp=None,
    logger=None,
    standardize=False,
    linesep=b"\r\n",
):
    # type: (bytes, bytes, bytes, bytes, bytes, bytes, list, any, any, bool) -> list
    """Sign an RFC822 message and return the ARC set header lines for the next instance
    @param message: an RFC822 formatted message (with either \\n or \\r\\n line endings)
    @param selector: the DKIM selector value for the signature
    @param domain: the DKIM domain value for the signature
    @param privkey: a PKCS#1 private key in base64-encoded text form
    @param srv_id: the authserv_id used to identify the ADMD's AR headers and to use for
        ARC authserv_id
    @param signature_algorithm: the signing algorithm to use when signing
    @param include_headers: a list of strings indicating which headers are to be signed
        (default all headers not listed as SHOULD NOT sign)
    @param timestamp: the time in integer seconds when the message is sealed
        (default is int(time.time) based on platform, can be string or int)
    @param logger: a logger to which info info will be written (default None)
    @param linesep: use this line seperator for folding the headers
    @return: A list containing the ARC set of header fields for the next instance
    @raise DKIMException: when the message, include_headers, or key are badly formed.
    """
    a = ARC(message, logger=logger, signature_algorithm=b"rsa-sha256", linesep=linesep)
    if not include_headers:
        include_headers = a.default_sign_headers()
    return a.sign(
        selector,
        domain,
        privkey,
        srv_id,
        include_headers=include_headers,
        timestamp=timestamp,
        standardize=standardize,
    )


def arc_verify(message, logger=None, dnsfunc=get_txt, minkey=1024, timeout=5):
    # type: (bytes, any, function, int) -> tuple
    """Verify the ARC chain on an RFC822 formatted message.
    @param message: an RFC822 formatted message (with either \\n or \\r\\n line endings)
    @param logger: a logger to which info info will be written (default None)
    @param dnsfunc: an optional function to lookup TXT resource records
    @param minkey: the minimum key size to accept
    @param timeout: number of seconds for DNS lookup timeout (default = 5)
    @return: three-tuple of (CV Result (CV_Pass, CV_Fail or CV_None), list of
    result dictionaries, result reason)
    """
    a = ARC(message, logger=logger, minkey=minkey, timeout=5)
    try:
        return a.verify(dnsfunc=dnsfunc)
    except DKIMException as x:
        if logger is not None:
            logger.error(f"{x}")
        return CV_Fail, [], f"{x}"


# A resolver wrapper around dnslib.py
# stolen wholesale from https://github.com/TheRook/subbrute
# thanks Rook
class Resolver:
    # Google's DNS servers are only used if zero resolvers are specified by the user.
    pos = 0
    rcode = ""
    wildcards = {}
    failed_code = False
    last_resolver = ""

    def __init__(self, nameservers=["8.8.8.8", "8.8.4.4"]):
        self.nameservers = nameservers

    def query(self, hostname, query_type="ANY", name_server=False, use_tcp=True):
        ret = []
        response = None
        if not name_server:
            name_server = self.get_ns()
        else:
            self.wildcards = {}
            self.failed_code = None
        self.last_resolver = name_server
        query = dnslib.DNSRecord.question(hostname, query_type.upper().strip())
        try:
            response_q = query.send(name_server, 53, use_tcp)
            if response_q:
                response = dnslib.DNSRecord.parse(response_q)
            else:
                raise OSError("Empty Response")
        except Exception as e:
            # IOErrors are all conditions that require a retry.
            raise OSError(str(e))
        if response:
            self.rcode = dnslib.RCODE[response.header.rcode]
            for r in response.rr:
                try:
                    rtype = str(dnslib.QTYPE[r.rtype])
                except Exception:  # Server sent an unknown type:
                    rtype = str(r.rtype)
                # Fully qualified domains may cause problems for other tools that
                # use subbrute's output.
                rhost = str(r.rname).rstrip(".")
                ret.append((rhost, rtype, str(r.rdata)))
            # What kind of response did we get?
            if self.rcode not in ["NOERROR", "NXDOMAIN", "SERVFAIL", "REFUSED"]:
                trace("!Odd error code:", self.rcode, hostname, query_type)
            # Is this a perm error?  We will have to retry to find out.
            if self.rcode in ["SERVFAIL", "REFUSED", "FORMERR", "NOTIMP", "NOTAUTH"]:
                raise OSError("DNS Failure: " + hostname + " - " + self.rcode)
            # Did we get an empty body and a non-error code?
            if not ret and self.rcode != "NXDOMAIN":
                raise OSError("DNS Error - " + self.rcode + " - for:" + hostname)
        return ret

    def was_successful(self):
        ret = False
        if (
            self.failed_code and self.rcode != self.failed_code
        ) or self.rcode == "NOERROR":
            ret = True
        return ret

    def get_returncode(self):
        return self.rcode

    def get_ns(self):
        if self.pos >= len(self.nameservers):
            self.pos = 0
        ret = self.nameservers[self.pos]
        # we may have metadata on how this resolver fails
        try:
            ret, self.wildcards, self.failed_code = ret
        except Exception:
            self.wildcards = {}
            self.failed_code = None
        self.pos += 1
        return ret

    def add_ns(self, resolver):
        if resolver:
            self.nameservers.append(resolver)

    def get_authoritative(self, hostname):
        ret = []
        while not ret and hostname.count(".") >= 1:
            try:
                trace("Looking for nameservers:", hostname)
                nameservers = self.query(hostname, "NS")
            except OSError:  # lookup failed.
                nameservers = []
            for n in nameservers:
                # A DNS server could return anything.
                rhost, record_type, record = n
                if record_type == "NS":
                    # Return all A records for this NS lookup.
                    a_lookup = self.query(record.rstrip("."), "A")
                    for a_host, a_type, a_record in a_lookup:
                        ret.append(a_record)
                # If a nameserver wasn't found try the parent of this sub.
            hostname = hostname[hostname.find(".") + 1 :]
        return ret

    def get_last_resolver(self):
        return self.last_resolver


# Toggle debug output
verbose = False


def trace(*args, **kwargs):
    if verbose:
        for a in args:
            sys.stderr.write(str(a))
            sys.stderr.write(" ")
        sys.stderr.write("\n")


class SpfRecord:
    def __init__(self, domain):
        self.version = None
        self.record = None
        self.mechanisms = None
        self.all_string = None
        self.domain = domain
        self.recursion_depth = 0

    def __str__(self):
        return self.record

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def get_redirected_record(self):
        if self.recursion_depth >= 10:
            return SpfRecord(self.get_redirect_domain())
        redirect_domain = self.get_redirect_domain()
        if redirect_domain is not None:
            redirect_record = SpfRecord.from_domain(redirect_domain)
            redirect_record.recursion_depth = self.recursion_depth + 1
            return redirect_record

    def get_redirect_domain(self):
        redirect_domain = None
        if self.mechanisms is not None:
            for mechanism in self.mechanisms:
                redirect_mechanism = re.match("redirect=(.*)", mechanism)
                if redirect_mechanism is not None:
                    redirect_domain = redirect_mechanism.group(1)
            return redirect_domain

    def get_include_domains(self):
        include_domains = []
        if self.mechanisms is not None:
            for mechanism in self.mechanisms:
                include_mechanism = re.match("include:(.*)", mechanism)
                if include_mechanism is not None:
                    include_domains.append(include_mechanism.group(1))
            return include_domains
        return []

    def get_include_records(self):
        if self.recursion_depth >= 10:
            return {}
        include_domains = self.get_include_domains()
        include_records = {}
        for domain in include_domains:
            try:
                include_records[domain] = SpfRecord.from_domain(domain)
                include_records[domain].recursion_depth = self.recursion_depth + 1
            except OSError as e:
                logging.exception(e)
                include_records[domain] = None
        return include_records

    def _is_all_mechanism_strong(self):
        strong_spf_all_string = True
        if self.all_string is not None:
            if not (self.all_string == "~all" or self.all_string == "-all"):
                strong_spf_all_string = False
        else:
            strong_spf_all_string = False
        return strong_spf_all_string

    def _is_redirect_mechanism_strong(self):
        redirect_domain = self.get_redirect_domain()

        if redirect_domain is not None:
            redirect_mechanism = SpfRecord.from_domain(redirect_domain)

            if redirect_mechanism is not None:
                return redirect_mechanism.is_record_strong()
            return False
        return False

    def _are_include_mechanisms_strong(self):
        include_records = self.get_include_records()
        for record in include_records:
            if (
                include_records[record] is not None
                and include_records[record].is_record_strong()
            ):
                return True
        return False

    def is_record_strong(self):
        strong_spf_record = self._is_all_mechanism_strong()
        if strong_spf_record is False:
            redirect_strength = self._is_redirect_mechanism_strong()
            include_strength = self._are_include_mechanisms_strong()

            strong_spf_record = False

            if redirect_strength is True:
                strong_spf_record = True

            if include_strength is True:
                strong_spf_record = True
        return strong_spf_record

    @staticmethod
    def from_spf_string(spf_string, domain):
        if spf_string is not None:
            spf_record = SpfRecord(domain)
            spf_record.record = spf_string
            spf_record.mechanisms = _extract_mechanisms(spf_string)
            spf_record.version = _extract_version(spf_string)
            spf_record.all_string = _extract_all_mechanism(spf_record.mechanisms)
            return spf_record
        return SpfRecord(domain)

    @staticmethod
    def from_domain(domain):
        spf_string = get_spf_string_for_domain(domain)
        if spf_string is not None:
            return SpfRecord.from_spf_string(spf_string, domain)
        return SpfRecord(domain)


def _extract_version(spf_string):
    version_pattern = "^v=(spf.)"
    version_match = re.match(version_pattern, spf_string)
    if version_match is not None:
        return version_match.group(1)
    return None


def _extract_all_mechanism(mechanisms):
    all_mechanism = None
    for mechanism in mechanisms:
        if re.match(".all", mechanism):
            all_mechanism = mechanism
    return all_mechanism


def _find_unique_mechanisms(initial_mechanisms, redirected_mechanisms):
    return [x for x in redirected_mechanisms if x not in initial_mechanisms]


def _extract_mechanisms(spf_string):
    spf_mechanism_pattern = (
        r"(?:((?:\+|-|~)?(?:a|mx|ptr|include"
        "|ip4|ip6|exists|redirect|exp|all)"
        r"(?:(?::|=|/)?(?:\S*))?) ?)"
    )
    spf_mechanisms = re.findall(spf_mechanism_pattern, spf_string)

    return spf_mechanisms


def _merge_txt_record_strings(txt_record):
    # SPF spec requires that TXT records containing multiple strings be cat'd together.
    string_pattern = re.compile('"([^"]*)"')
    txt_record_strings = string_pattern.findall(txt_record)
    return "".join(txt_record_strings)


def _match_spf_record(txt_record):
    clean_txt_record = _merge_txt_record_strings(txt_record)
    spf_pattern = re.compile("^(v=spf.*)")
    potential_spf_match = spf_pattern.match(str(clean_txt_record))
    return potential_spf_match


def _find_record_from_answers(txt_records):
    spf_record = None
    for record in txt_records:
        potential_match = _match_spf_record(record[2])
        if potential_match is not None:
            spf_record = potential_match.group(1)
    return spf_record


def get_spf_string_for_domain(domain):
    try:
        txt_records = Resolver().query(domain, query_type="TXT")
        return _find_record_from_answers(txt_records)
    except OSError:
        # This is returned usually as a NXDOMAIN, which is expected.
        return None


def fix_malformed_eml_content(content_bytes: bytes) -> bytes:
    """Fix malformed eml bytes content if exist.
    fix for b/356792519

    Args:
        content_bytes (bytes): eml file content.

    Returns:
        bytes: fixed eml content.

    """
    ep_obj = eml_parser.EmlParser()
    parsed_eml = ep_obj.decode_email_bytes(content_bytes)
    main_content_type = parsed_eml["header"]["header"].get("content-type", [])
    if (
        len(main_content_type) > 1
        and str(main_content_type[0]) == "text/plain"
        and "multipart" in str(main_content_type[1])
    ):
        text_content_type = str(main_content_type[0]).encode("utf-8")
        next_content_type = str(main_content_type[1]).encode("utf-8")
        content_bytes = content_bytes.replace(text_content_type, next_content_type, 1)

    return content_bytes


def extract_valid_ips_from_body(body: str) -> list[str]:
    """Extract valid IPs from body.

    Args:
        body (str): string to extract valid ips.

    Retruns:
        list[str]: list of valid ips.
    """
    candidates = re.findall(r"\b[0-9a-fA-F:.]+\b", body)
    return [
        candidate for candidate in candidates
        if valid_ipv4(candidate) or valid_ipv6(candidate)
    ]
