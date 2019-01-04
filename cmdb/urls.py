from django.conf.urls import url
from cmdb.views import cmdb_pool, product_info, tree, user_auth

urlpatterns = [
    # CMDB pool
    url(r'^/cmdb_pool/cmdb_pool', cmdb_pool.cmdb_pool, name="cmdb-pool"),
    url(r'^/cmdb_pool/cmdb_update', cmdb_pool.cmdb_update, name="cmdb-pool-update"),
    url(r'^/cmdb_pool/cmdb_delete', cmdb_pool.cmdb_delete, name="cmdb-pool-delete"),

    # CMDB product info
    url(r'^/product_info/product_list', product_info.product_list, name="cmdb-product-list"),
    url(r'^/product_info/commit_product', product_info.commit_product, name="cmdb-product-commit-product"),
    url(r'^/product_info/delete_product', product_info.delete_product, name="cmdb-product-delete-product"),

    # CMDB tree info
    url(r'^/tree/tree_info', tree.tree_info, name="cmdb-tree-info"),
    url(r'^/tree/get_node_info', tree.get_node_info, name="cmdb-get-tree-node-info"),
    url(r'^/tree/change_father_node', tree.change_father_node, name="cmdb-change-father-node"),
    url(r'^/tree/get_unused_ip_from_cmdb_pool', tree.get_unused_ip_from_cmdb_pool, name="cmdb-get-unused-ip-from-cmdb-pool"),
    url(r'^/tree/get_prod_list', tree.get_prod_list, name="cmdb-get-product-list"),
    url(r'^/tree/save_node_change', tree.save_node_change, name="cmdb-save-node-change"),
    url(r'^/tree/create_node', tree.create_node, name="cmdb-create-node"),
    url(r'^/tree/delete_node', tree.delete_node, name="cmdb-delete-tree-node"),


    # CMDB user ssh key
    url(r'^/user_auth/get_user_info', user_auth.get_user_info, name="cmdb-user-auth-info"),
    url(r'^/user_auth/tree_node_list', user_auth.tree_node_list, name="cmdb-user-auth-tree-node-list"),
    url(r'^/user_auth/commit_user_auth', user_auth.commit_user_auth, name="cmdb-user-auth-commit-user-auth"),
    url(r'^/user_auth/delete_user', user_auth.delete_user_auth, name="cmdb-user-auth-delete-user"),
    url(r'^/user_auth/sync_auth', user_auth.sync_auth, name="cmdb-sync-auth"),
]