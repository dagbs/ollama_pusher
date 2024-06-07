import os

class Template:
    def __init__(self):
        self._from = ''
        self._template = """"""
        self._parameter = {
            'num_ctx': 4096,
            'stop': [
                "<|im_start|>",
                "<|im_end|>"
            ]
        }

    def use_template(self, template=None):
        if template is None:
            raise Exception('missing template name')
        
        self._template = open(os.path.join('template', template.lower() + '.txt'), 'r').read()

    def _format_parameters(self, parameter=None):
        if parameter is None:
            parameter = self._parameter

        res = ''
        for key, value in parameter.items():
            if isinstance(value, list):
                for v in value:
                    res += 'PARAMETER ' + key + ' "' + str(v) + '"\n'
            else:
                res += 'PARAMETER ' + key  +  ' '  + str(value) + '\n'

        return res.strip()

    
    def set_model(self, model):
        self._from = 'FROM ' + model

    def get(self):
        return '\n'.join([self._from, 
                         self._template,
                         self._format_parameters()])