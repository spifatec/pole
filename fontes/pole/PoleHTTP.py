#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import httplib
import cStringIO
import gzip
import zlib

class Conexao(object):
    _cabecalho_iceweasel = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:10.0.12) Gecko/20100101 Firefox/10.0.12 Iceweasel/10.0.12',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-br,pt;q=0.8,en-us;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    def __init__(self, servidor, porta = -1, protocolo = '', timeout = 5):
        if not protocolo:
            prot_serv = servidor.split('://', 1)
            if len(prot_serv) == 2:
                protocolo, servidor = prot_serv
        protocolo = protocolo.lower()
        if not protocolo:
            protocolo = 'https' if porta == 443 else 'http'
        elif protocolo not in ('http', 'https'):
            raise Exception('Protocolo "%s" inválido!' % protocolo)
        if porta == -1:
            porta = 443 if protocolo == 'https' else 80
        if protocolo == 'https':
            self.conexao = httplib.HTTPSConnection(servidor, porta, timeout = timeout)
        else:
            self.conexao = httplib.HTTPConnection(servidor, porta, timeout = timeout)
        self.servidor = servidor
        self.porta = porta
        self.protocolo = protocolo
        self._timeout = timeout
        self.cabecalhos = dict(self._cabecalho_iceweasel)
        self.cabecalhos['Host'] = self.servidor
        self.cookies = {}

    def renovar_conexao(self):
        self.fechar()
        if self.protocolo == 'https':
            self.conexao = httplib.HTTPSConnection(self.servidor, self.porta, timeout = self._timeout)
        else:
            self.conexao = httplib.HTTPConnection(self.servidor, self.porta, timeout = self._timeout)

    def timeout(self, timeout):
        if not self.conexao:
            raise Exception('Não conectado!')
        self._timeout = timeout
        self.conexao.sock.settimeout(timeout)

    def _descomprimir(self, dados, encoding):
        if encoding == 'gzip':
            io = cStringIO.StringIO(dados)
            g = gzip.GzipFile(fileobj = io, mode = 'rb')
            ungziped = g.read()
            g.close()
            return ungziped
        if encoding == 'deflate':
            return zlib.decompress(dados)
        return dados

    def obter_dados(self, caminho, dados = '', atualiza_referer = True, mais_cabecalhos = None, seguir = True):
        if not self.conexao:
            raise Exception('Não conectado!')
        metodo = 'POST' if dados else 'GET'
        cabecalhos = dict(self.cabecalhos)
        if dados:
            cabecalhos['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        cabecalhos['Content-Length'] = len(dados)
        if mais_cabecalhos is not None:
            for cabec in mais_cabecalhos:
                cabecalhos[cabec] = mais_cabecalhos[cabec]
        self.conexao.request(metodo, caminho, dados, cabecalhos)
        tempo =  time.time()
        resposta = self.conexao.getresponse()
        tempo =  int(round((time.time() - tempo) * 1000))
        conteudo = self._descomprimir(resposta.read(), resposta.getheader('content-encoding'))
        if atualiza_referer and resposta.status == 200:
            self.cabecalhos['Referer'] = "%s://%s%s" % (self.protocolo, self.servidor, caminho.split('?', 1)[0])
        novos_cookies = {}
        for h in resposta.getheaders():
            if h[0].lower() == 'set-cookie':
                for cookie in h[1].split(','):
                    cookie = cookie.split(';', 1)[0]
                    if '=' in cookie:
                        cookie, valor = cookie.split('=', 1)
                        novos_cookies[cookie] = valor
        #novos_cookies = dict([h[1].split(';', 1)[0].split('=') for h in resposta.getheaders() if h[0].lower() == 'set-cookie'])
        if novos_cookies:
            for k, v in novos_cookies.items():
                self.cookies[k] = v
            self.cabecalhos['Cookie'] = ';'.join([k + '=' + v for k,v in self.cookies.items()])
        if seguir and resposta.status in (302, 303) and resposta.getheader('location'):
            return self.obter_dados(resposta.getheader('location').split(';')[0], '', atualiza_referer, mais_cabecalhos, seguir)
        return {'status': resposta.status, 'descrição': resposta.reason,
                'cabeçalhos': resposta.getheaders(), 'cookies': self.cookies,
                'conteúdo': conteudo, 'tempo': tempo}

    def fechar(self):
        if self.conexao:
            self.conexao.close()
            self.conexao = None
