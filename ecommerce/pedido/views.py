from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView
from django.views import View
from django.http import HttpResponse
from django.contrib import messages
from produto.models import Variacao
from utils import utils
from .models import Pedido, ItemPedido
from django.shortcuts import reverse


class SalvarPedido(View):
    template_name = 'pedidio/pagar.html'

    def get(self, *args, **kwargs):

        if not self.request.user.is_authenticated:
            messages.error(self.request,
                           'Você precisa fazer login')
            return redirect('perfil:criar')

        if not self.request.session.get('carrinho'):
            messages.error(self.request,
                           'Carrinho vazio')
            return redirect('produto:lista')

        carrinho = self.request.session.get('carrinho')
        carrinho_variacao_ids = [v for v in carrinho]
        bd_variacoes = list(Variacao.objects.select_related('produto').filter(
            id__in=carrinho_variacao_ids))

        for variacao in bd_variacoes:
            vid = str(variacao.id)
            estoque = variacao.estoque
            qtd_carrinho = carrinho[vid]['quantidade']
            preco_unt = carrinho[vid]['preco_unitario']
            preco_unt_promo = carrinho[vid]['preco_unitario_promocional']

            error_msg_estoque = ''

            if estoque < qtd_carrinho:
                carrinho[vid]['quantidade'] = estoque
                carrinho[vid]['preco_quantitativo'] = estoque * preco_unt
                carrinho[vid]['preco_quantitativo_promocional'] = estoque * \
                    preco_unt_promo

                error_msg_estoque = 'Estoque insuficiente para alguns produtos do seu carrinho'

                if error_msg_estoque:
                    messages.error(self.request, error_msg_estoque)
                    self.request.session.save()
                    return redirect('produto:carrinho')

            qtd_total_carrinho = utils.cart_total_qtd(carrinho)
            valor_total_carrinho = utils.cart_totals(carrinho)

            pedido = Pedido(usuario=self.request.user, total=valor_total_carrinho,
                            qtd_total=qtd_total_carrinho, status='C',)

            pedido.save()

            ItemPedido.objects.bulk_create(
                [
                    ItemPedido(
                        pedido=pedido,
                        produto=v['produto_nome'],
                        produto_id=v['produto_id'],
                        variacao=v['variacao_nome'],
                        variacao_id=v['variacao_id'],
                        preco=v['preco_quantitativo'],
                        preco_promocional=v['preco_quantitativo_promocional'],
                        quantidade=v['quantidade'],
                        imagem=v['imagem'],

                    ) for v in carrinho.values()
                ]
            )

        contexto = {
            'qtd_total_carrinho': qtd_total_carrinho,
            'valor_total_carrinho': valor_total_carrinho,
        }

        del self.request.session['carrinho']
        # render(self.request, self.template_name, contexto)
        return redirect(reverse(
            'pedido:pagar',
            kwargs={
                'pk': pedido.pk
            }
        ))


class DispatchLoginRequiredMixing(View):
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('perfil:criar')

        return super().dispatch(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs


class Pagar(DispatchLoginRequiredMixing, DetailView):
    template_name = 'pedido/pagar.html'
    model = Pedido
    pk_url_kwarg = 'pk'
    context_object_name = 'pedido'


class Detalhe(DispatchLoginRequiredMixing, DetailView):
    model = Pedido
    context_object_name = 'pedido'
    template_name = 'pedido/detalhe.html'
    pk_url_kwarg = 'pk'


class Lista(DispatchLoginRequiredMixing, ListView):
    model = Pedido
    context_object_name = 'pedidos'
    template_name = 'pedido/lista.html'
    paginate_by = 10
    ordering = ['-id']
