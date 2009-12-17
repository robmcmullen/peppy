'''

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

class ITopicTreeTraverser:
    '''
    Topic tree traverser. Provides the traverse() method
    which traverses a topic tree and calls self._onTopic() for
    each topic in the tree that satisfies self._accept().
    Additionally it calls self._startChildren() whenever it
    starts traversing the subtopics of a topic, and
    self._endChildren() when it is done with the subtopics.
    Finally, it calls self._doneTraversal() when traversal
    has been completed.

    Derive from ITopicTreeTraverser and override one or more of the
    four self._*() methods described above. Call traverse()
    on instances to "execute" the traversal.
    '''

    DEPTH   = 'Depth first through topic tree'
    BREADTH = 'Breadth first through topic tree'
    MAP     = 'Sequential through topic manager\'s topics map'

    def _accept(self, topicObj):
        '''Override this to filter nodes of topic tree. Must return
        True (accept node) of False (reject node). Note that rejected
        nodes cause traversal to move to next branch (no children
        traversed).'''
        return True

    def _startTraversal(self):
        '''Override this to define what to do when traversal() starts.'''
        pass

    def _onTopic(self, topicObj):
        '''Override this to define what to do for each node.'''
        pass

    def _startChildren(self):
        '''Override this to take special action whenever a
        new level of the topic hierarchy is started (e.g., indent
        some output). '''
        pass

    def _endChildren(self):
        '''Override this to take special action whenever a
        level of the topic hierarchy is completed (e.g., dedent
        some output). '''
        pass

    def _doneTraversal(self):
        '''Override this to take special action when traversal done.'''
        pass

    def traverse(self, topicObj, how=DEPTH, onlyFiltered=True):
        '''Start traversing tree at topicObj. Note that topicObj is a
        Topic object, not a topic name. The how defines if tree should
        be traversed breadth or depth first. If onlyFiltered is
        False, then all nodes are accepted (_accept(node) not called).
        '''
        if how == self.MAP:
            raise NotImplementedError('not yet available')

        self._startTraversal()

        if how == self.BREADTH:
            self.__traverseBreadth(topicObj, onlyFiltered)
        else: #if how == self.DEPTH:
            self.__traverseDepth(topicObj, onlyFiltered)

        self._doneTraversal()

    def __traverseBreadth(self, topicObj, onlyFiltered):
        def extendQueue(subtopics):
            topics.append(self._startChildren)
            topics.extend(subtopics)
            topics.append(self._endChildren)

        topics = [topicObj]
        while topics:
            topicObj = topics.pop(0)

            if topicObj in (self._startChildren, self._endChildren):
                topicObj()
                continue

            if onlyFiltered:
                if self._accept(topicObj):
                    extendQueue( topicObj.getSubtopics() )
                    self._onTopic(topicObj)
            else:
                extendQueue( topicObj.getSubtopics() )
                self._onTopic(topicObj)

    def __traverseDepth(self, topicObj, onlyFiltered):
        def extendStack(topicTreeStack, subtopics):
            topicTreeStack.insert(0, self._endChildren) # marker functor
            # put subtopics in list in alphabetical order
            subtopicsTmp = subtopics
            subtopicsTmp.sort(reverse=True, key=topicObj.__class__.getName)
            for sub in subtopicsTmp:
                topicTreeStack.insert(0, sub) # this puts them in reverse order
            topicTreeStack.insert(0, self._startChildren) # marker functor

        topics = [topicObj]
        while topics:
            topicObj = topics.pop(0)

            if topicObj in (self._startChildren, self._endChildren):
                topicObj()
                continue

            if onlyFiltered:
                if self._accept(topicObj):
                    extendStack( topics, topicObj.getSubtopics() )
                    self._onTopic(topicObj)
            else:
                extendStack( topics, topicObj.getSubtopics() )
                self._onTopic(topicObj)


