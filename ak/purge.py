from .base import Akamai


class Purge(Akamai):

    def invalidateByCPCode(self, network, objects):
        path = f"/ccu/v3/invalidate/cpcode/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result

    def invalidateByCacheTag(self, network, objects):
        path = f"/ccu/v3/invalidate/tag/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result

    def invalidateByUrl(self, network, objects):
        path = f"/ccu/v3/invalidate/url/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result

    def deleteByCPCode(self, network, objects):
        path = f"/ccu/v3/delete/cpcode/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result

    def deleteByCacheTag(self, network, objects):
        path = f"/ccu/v3/delete/tag/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result

    def deleteByUrl(self, network, objects):
        path = f"/ccu/v3/delete/url/{network}"
        body = {"objects": objects}
        result = self.post(path=path, body=body)
        return result
