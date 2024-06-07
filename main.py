import os
import shutil
import sys
import ollama
from modelfile import Template
from huggingface_hub import hf_hub_download, HfFileSystem

# https://github.com/ollama/ollama/blob/main/docs/import.md#publishing-your-model-optional--early-alpha
# OLLAMA_REPO_OWNER is your username on ollama.com
# you need to have your ollama public key added to your ollama account to be able to publish models
OLLAMA_REPO_OWNER = 'dagbs'

# CLEAN_DEFAULT will remove the build directory and the model directory before building a new one as well as cleaning up post publish
# this happens on every quant
CLEAN_DEFAULT = True

# DEEP_CLEAN_DEFAULT will remove the models from your local ollama instance after it has been published
DEEP_CLEAN_DEFAULT = True


fs = HfFileSystem()

def do_repo(repo_id, *args):
    for file in fs.ls(repo_id, detail=True):
        filename = file['name'].rsplit('/', 1)[1]
        if len(file['name'].replace(repo_id, '').replace(filename, '').replace('/', '')) > 0:
            print(f"Skipping {file['name']} because it is in a folder")
            continue

        if file['size'] > 50 * 1024**3:
            print(f"Skipping {file['name']} because it's too large")
            continue

        if not filename.endswith('.gguf'):
            print(f"Skipping {file['name']} because it's not a .gguf file")
            continue
        
        try:
            do_quant(repo_id, filename)
        except Exception as e:
            print(f"Skipping {file['name']} because of error: {e}")
            

def _get_quant_from_filename(filename):
    filename = filename.lower()    
    if filename.endswith('.gguf'):
        if '-iq' in filename:
            return filename[filename.rfind('iq'):].split('.')[0]
        elif '-f' in filename:
            return filename[filename.rfind('f'):].split('.')[0]
        else:
            return filename[filename.rfind('q'):].split('.')[0]
    else:
        raise ValueError("Invalid model file name")

def do_quant(repo_id, filename, quant=None, latest=None, pre_clean=CLEAN_DEFAULT, post_clean=CLEAN_DEFAULT, deep_clean=DEEP_CLEAN_DEFAULT):
    if quant is None:
        quant = _get_quant_from_filename(filename).lower()
    else:
        quant = quant.lower()

    # default of latest?
    if latest is None:
        latest = quant == 'q4_0' or quant == 'q4_k' or quant == 'q4_k_m'
    else:
        latest = bool(latest)
    pre_clean = bool(pre_clean)
    post_clean = bool(post_clean)

    ## WHAT DO WE HAVE?!?
    model_name = repo_id.split('/')[1].lower().replace('-gguf', '')
    print('model_name> ' + OLLAMA_REPO_OWNER + '/' + model_name + ':' + quant)

    # create build folder if it doesnt exist
    if not os.path.exists('build'):
        os.makedirs('build')
    
    if pre_clean and os.path.exists('build'):
        shutil.rmtree('build', ignore_errors=True)

    if not os.path.exists(os.path.join('build', filename)):
        print('downloading...')
        try:
            hf_hub_download(repo_id, filename, local_dir='build')
        except Exception as e:
            raise Exception('file not available?')
    modelfile = Template()
    modelfile.set_model(os.path.abspath(os.path.join('build', filename)))
    modelfile.use_template('chatml')

    print('creating...')
    for res in ollama.create(model=model_name + ':' + quant, modelfile=modelfile.get(), stream=True):
        print(res['status'])

    print('copying...')
    try:
        ollama.copy(source=model_name + ':' + quant, destination=OLLAMA_REPO_OWNER + '/' + model_name + ':' + quant)
    except Exception as e:
        if 'already exists' in str(e):
            print('already exists?')
        else:
            raise Exception(str(e))

    if latest:
        try:
            ollama.copy(source=model_name + ':' + quant, destination=OLLAMA_REPO_OWNER + '/' + model_name + ':latest')
        except Exception as e:
            if 'already exists' in str(e):
                print('already exists?')
            else:
                raise Exception(str(e))

    print('uploading...')
    last_status = ''
    for res in ollama.push(OLLAMA_REPO_OWNER + '/' + model_name + ':' + quant, stream=True):
        if last_status != res['status']:
            print(res['status'])
            last_status = res['status']
            
    if latest:
        last_status = ''
        for res in ollama.push(OLLAMA_REPO_OWNER + '/' + model_name + ':latest', stream=True):
            if last_status != res['status']:
                print(res['status'])
                last_status = res['status']

    if post_clean:
        print('deleting local temporary models...')
        res = ollama.delete(model=model_name  +  ':'  + quant)
        print(res)

        if latest:
            try:
                res = ollama.delete(model=OLLAMA_REPO_OWNER + '/' + model_name + ':latest')
                print(res)
            except Exception as e:
                print(str(e))

        if deep_clean:
            try:
                res = ollama.delete(model=OLLAMA_REPO_OWNER + '/' + model_name +  ':'  + quant)
                print(res)
            except Exception as e:
                print(str(e))

        print('deleting temporary models...')
        shutil.rmtree('build', ignore_errors=True)

    print('done!')

if __name__ == "__main__":
    # main(*sys.argv[1:])
    do_repo(*sys.argv[1:])    