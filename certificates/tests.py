import unittest,tempfile,datetime,ipaddress,json,os
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization
from manager import sync_certificate
class Certificates(unittest.TestCase):
    def issue(self,folder,name,ip='203.0.113.20',key=None,expired=False):
        key=key or ec.generate_private_key(ec.SECP256R1());ca=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc)
        cert=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'test')])).issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'test CA')])).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=3)).not_valid_after(now+datetime.timedelta(days=-1 if expired else 2)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]),critical=False).sign(ca,hashes.SHA256())
        c=Path(folder)/(name+'.crt');k=Path(folder)/(name+'.key');c.write_bytes(cert.public_bytes(serialization.Encoding.PEM));k.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));return c,k
    def test_valid_rotation_permissions_and_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            c,k=self.issue(d,'first');sync_certificate(c,k,'203.0.113.20',Path(d));bundle=Path(d)/'tls-bundle.json';first=json.loads(bundle.read_text());self.assertTrue(first['trustedIP']);self.assertEqual(os.stat(bundle).st_mode&0o777,0o600)
            c2,k2=self.issue(d,'second');sync_certificate(c2,k2,'203.0.113.20',Path(d));self.assertNotEqual(first['cert'],json.loads(bundle.read_text())['cert']);before=bundle.read_bytes()
            for cert,key,ip in [(c,k2,'203.0.113.20'),(c,k,'203.0.113.21'),(*self.issue(d,'expired',expired=True),'203.0.113.20')]:
                with self.assertRaises(Exception):sync_certificate(cert,key,ip,Path(d))
                self.assertEqual(before,bundle.read_bytes())
if __name__=='__main__':unittest.main()
