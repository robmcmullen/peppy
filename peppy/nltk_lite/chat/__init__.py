"""Wrapper around nltk_lite chatbots.

The module defines a single dictionary that maps a text name to a
tuple, where the tuple contains the chatbot object and the
introduction message.
"""

from eliza import eliza
from zen import zen
from iesha import iesha
from rude import rude

chatbots={'eliza': [eliza, "Hello.  How are you feeling today?"],
          'zen': [zen, "Welcome, my child."],
          'iesha': [iesha, "hi!! i'm iesha! who r u??!"],
          'rude': [rude, "I suppose I should say hello."],
          }

__all__ = ['chatbots']
