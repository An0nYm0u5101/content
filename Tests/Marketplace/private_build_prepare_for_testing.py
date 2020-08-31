import argparse
import sys
import os
from Tests.Marketplace.marketplace_services import GCPConfig, init_storage_client, Pack
from Tests.Marketplace.upload_packs import download_and_extract_index, extract_packs_artifacts
from demisto_sdk.commands.common.tools import str2bool


def option_handler():
    """Validates and parses script arguments.

    Returns:
        Namespace: Parsed arguments object.

    """
    parser = argparse.ArgumentParser(description="Store packs in cloud storage.")
    # disable-secrets-detection-start
    parser.add_argument('-p', '--pack_name', help="Name of the private pack to upload.", required=True)
    parser.add_argument('-a', '--artifacts_path', help="The full path of packs artifacts", required=True)
    parser.add_argument('-e', '--extract_path', help="Full path of folder to extract wanted packs", required=True)
    parser.add_argument('-s', '--service_account',
                        help=("Path to gcloud service account, is for circleCI usage. "
                              "For local development use your personal account and "
                              "authenticate using Google Cloud SDK by running: "
                              "`gcloud auth application-default login` and leave this parameter blank. "
                              "For more information go to: "
                              "https://googleapis.dev/python/google-api-core/latest/auth.html"),
                        required=False)

    parser.add_argument('-i', '--id_set_path', help="The full path of id_set.json", required=False)
    parser.add_argument('-d', '--pack_dependencies', help="Full path to pack dependencies json file.", required=False)

    parser.add_argument('-n', '--ci_build_number',
                        help="CircleCi build number (will be used as hash revision at index file)", required=True)
    parser.add_argument('-o', '--override_all_packs', help="Override all existing packs in cloud storage",
                        default=False, action='store_true', required=False)
    parser.add_argument('-k', '--key_string', help="Base64 encoded signature key used for signing packs.",
                        required=False)
    parser.add_argument('-sb', '--storage_base_path', help="Storage base path of the directory to upload to.",
                        required=False)
    parser.add_argument('-rt', '--remove_test_playbooks', type=str2bool,
                        help='Should remove test playbooks from content packs or not.', default=True)
    parser.add_argument('-enc', '--encrypt_pack', type=str2bool,
                        help='Should encrypt pack or not.', default=False)
    parser.add_argument('-ek', '--encryption_key', type=str,
                        help='The encryption key for the pack, if it should be encrypted.', default='')

    # disable-secrets-detection-end
    return parser.parse_args()


def upload_premium_pack_to_private_testing_bucket(premium_pack, private_testing_repo_client, extract_destination_path):
    _, zip_pack_path = premium_pack.zip_pack(extract_destination_path, premium_pack._pack_name, False, '')
    premium_pack.upload_to_storage(zip_pack_path, premium_pack.latest_version, private_testing_repo_client, True)


def main():
    upload_config = option_handler()
    path_to_artifacts = upload_config.artifacts_path
    extract_destination_path = upload_config.extract_path
    service_account = upload_config.service_account
    pack_name = upload_config.pack_names
    storage_base_path = upload_config.storage_base_path

    if storage_base_path:
        GCPConfig.STORAGE_BASE_PATH = storage_base_path

    build_number = upload_config.ci_build_number
    override_all_packs = upload_config.override_all_packs
    signature_key = upload_config.key_string
    id_set_path = upload_config.id_set_path
    should_encrypt_pack = upload_config.encrypt_pack
    enc_key = upload_config.encryption_key
    packs_dependencies_mapping = load_json(upload_config.pack_dependencies) if upload_config.pack_dependencies else {}

    remove_test_playbooks = upload_config.remove_test_playbooks

    storage_client = init_storage_client(service_account)
    private_testing_bucket_client = storage_client.bucket(GCPConfig.PRODUCTION_PRIVATE_CI_BUCKET)
    public_prod_bucket_client = storage_client.bucket(GCPConfig.PRODUCTION_BUCKET)

    extract_packs_artifacts(path_to_artifacts, extract_destination_path)
    path_to_pack = os.path.join(extract_destination_path, pack_name)
    premium_pack = Pack(pack_name, path_to_pack)
    premium_pack.upload_to_storage()

    upload_premium_pack_to_private_testing_bucket(pack_name, private_testing_bucket_client)
    # index_folder_path, index_blob = download_and_extract_index(public_prod_bucket_client, extract_destination_path)