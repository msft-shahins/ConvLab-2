
import uuid
import requests

from convlab2.nlu.jointBERT.multiwoz import BERTNLU
from convlab2.dst.rule.multiwoz import RuleDST
from convlab2.policy.rule.multiwoz import RulePolicy
from convlab2.nlg import NLG
from convlab2.nlg.template.multiwoz import TemplateNLG
from convlab2.dialog_agent import Agent, PipelineAgent

from convlab2.util.analysis_tool.analyzer import Analyzer
from pprint import pprint
import random
import numpy as np
import torch
import logging

class CLAgent(Agent):
    
    def __init__(self, nlg: NLG, name: str):
        self.name = name
        self.nlg = nlg
        self.conversation_Id = str(uuid.uuid4())   
        self.url = "https://clwoz2.azurewebsites.net/api/multiwoz"
        self.logger = logging.getLogger(self.__class__.__name__)
        

    def response(self, observation):
        """Generate agent response given user input.

        The data type of input and response can be either str or list of tuples, condition on the form of agent.

        Example:
            If the agent is a pipeline agent with NLU, DST and Policy, then type(input) == str and
            type(response) == list of tuples.
        Args:
            observation (str or list of tuples):
                The input to the agent.
        Returns:
            response (str or list of tuples):
                The response generated by the agent.
        """
        try:
            prediction = self._get_CL_prediction(observation)
            model_response = self.nlg.generate(prediction)
        except Exception as e:
            self.logger.warning(f'calling to CL failed with {e}')
            model_response = ''
        self.logger.info(f'sys: {model_response}')
        return model_response

    def init_session(self):
        """Reset the class variables to prepare for a new session."""
        self.conversation_Id = str(uuid.uuid4())
    
    def state_replace(self, state):
        self.conversation_Id = state

    def state_return(self):
        return self.conversation_Id

    def _get_CL_prediction(self, utterance):
        request = {
            'input': utterance, 
            'id': self.conversation_Id
        }
        self.logger.info(f'user: {utterance}')
        response = requests.post(self.url, json=request)
        response.raise_for_status()
        self.logger.info(f'CLWoz: {response.text}')
        return response.json()

    def _http_ok(self, status_code):
        if status_code >= 200 and status_code < 300:
            return True
        else:
            return False

def set_seed(r_seed):
    random.seed(r_seed)
    np.random.seed(r_seed)
    torch.manual_seed(r_seed)


def test_end2end():
    # setup basic logging 
    logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
            datefmt="%m/%d/%Y %H:%M:%S",
            level=logging.INFO,
        )
    # template NLG
    sys_nlg = TemplateNLG(is_user=False)
    # assemble
    sys_agent = CLAgent(nlg=sys_nlg, name='sys')

    # BERT nlu trained on sys utterance
    user_nlu = BERTNLU(mode='sys', config_file='multiwoz_sys_context.json',
                       model_file='https://convlab.blob.core.windows.net/convlab-2/bert_multiwoz_sys_context.zip')
    # not use dst
    user_dst = None
    # rule policy
    user_policy = RulePolicy(character='usr')
    # template NLG
    user_nlg = TemplateNLG(is_user=True)
    # assemble
    user_agent = PipelineAgent(user_nlu, user_dst, user_policy, user_nlg, name='user')

    analyzer = Analyzer(user_agent=user_agent, dataset='multiwoz')

    set_seed(20200720)
    analyzer.comprehensive_analyze(sys_agent=sys_agent, model_name='CL-TemplateNLG', total_dialog=1)
    #analyzer.sample_dialog(sys_agent)

if __name__ == '__main__':
    test_end2end()
