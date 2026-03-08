import torch


class SubCosts:        
    def __call__(self, state, action=None):
        """
        Compute cost for a batch of states and (optional) actions.
        :param state: Tensor of shape [batch_size, nx]
        :param action: Tensor of shape [batch_size, nu]
        :return: cost: Tensor of shape [batch_size]
        """

        return cost
