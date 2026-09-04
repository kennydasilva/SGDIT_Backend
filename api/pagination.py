from rest_framework.pagination import PageNumberPagination


class PaginacaoPadrao(PageNumberPagination):
    """
    Paginação partilhada por todos os endpoints de listagem.
    ?page=2&page_size=50 (page_size limitado a 100 para evitar respostas gigantes)
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
