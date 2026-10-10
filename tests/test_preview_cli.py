import hashlib,json,subprocess,sys,tempfile,unittest,os
from pathlib import Path

class PreviewCliTests(unittest.TestCase):
    def test_success_stderr_existing_output_and_private_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'preview'
            args=[sys.executable,'-m','cbengine.preview','examples/demo.json','--out-dir',str(out)]
            first=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
            self.assertEqual(first.returncode,0);self.assertEqual(first.stdout,'')
            self.assertIn('report.html',first.stderr);self.assertIn('教学',first.stderr)
            before=hashlib.sha256((out/'result.json').read_bytes()).hexdigest()
            repeated=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
            self.assertEqual(repeated.returncode,2);self.assertIn('新目录',repeated.stderr)
            self.assertEqual(before,hashlib.sha256((out/'result.json').read_bytes()).hexdigest())
            spec=json.loads(Path('examples/demo.json').read_text(encoding='utf-8'));spec['as_of']='private-token-do-not-echo'
            source=root/'invalid.json';source.write_text(json.dumps(spec),encoding='utf-8')
            bad=subprocess.run([sys.executable,'-m','cbengine.preview',str(source),'--out-dir',str(root/'invalid-out')],capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
            self.assertEqual(bad.returncode,2);self.assertNotIn('private-token-do-not-echo',bad.stderr)
            self.assertIn('核对',bad.stderr)
    def test_machine_json_stdout_is_still_parseable(self):
        r=subprocess.run([sys.executable,'-m','cbengine.cli','examples/demo.json'],capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['dirty_price'],118.5)
        check=subprocess.run([sys.executable,'-m','cbengine.crosscheck','examples/crosscheck-flat.json'],capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
        self.assertEqual(check.returncode,0);self.assertEqual(json.loads(check.stdout)['type'],'fixed-cashflow-crosscheck')
