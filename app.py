from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
import boto3

from datetime import datetime
import time
import io
import os

# Obtendo as credenciais da aws salvas nas variaveis de ambiente
aws_access_key_id = os.getenv('aws_access_key_id') 
aws_secret_access_key = os.getenv('aws_secret_access_key')
aws_session_token = os.getenv("aws_session_token")

# Iniciar o WebDriver diretamente, sem especificar o caminho completo
driver = webdriver.Chrome()

try:
    # Navegar até a página desejada
    url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/ibov?language=pt-br'  # Substitua pela URL real da página
    driver.get(url)

    # Selecionar a opção "Setor de Atuação"
    select_element = Select(driver.find_element(By.ID, 'segment'))
    select_element.select_by_visible_text('Setor de Atuação')

    # Esperar a página carregar os dados
    time.sleep(2)

    # Fazer upload do arquivo no s3
    def save_df_to_s3_parquet(df, bucket, key):

        try:
            # Convertendo o DataFrame para formato Parquet em memória
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)

            # Conectando ao S3 e enviando o arquivo Parquet
            s3_client = boto3.client('s3', 
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_session_token=aws_session_token)

            s3_client.upload_fileobj(buffer, bucket, key)

            print(f'DataFrame salvo como Parquet em s3://{bucket}/{key}')
        except Exception as e:
            print(f'Erro ao salvar DataFrame como Parquet no S3: {str(e)}')
            raise e


    # Função para extrair dados de uma página
    def extract_data():
        try:
            table = driver.find_element(By.XPATH, '//table[@class="table table-responsive-sm table-responsive-md"]')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            page_data = []
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                cols = [col.text for col in cols]
                if len(cols) == 7:  # Certifique-se de que cada linha tenha exatamente 7 colunas
                    page_data.append(cols)
                else:
                    print(f"Linha ignorada devido ao número incorreto de colunas: {cols}")
            return page_data
        except Exception as e:
            print(f"Erro ao extrair dados: {e}")
            return []

    all_data = []

    while True:
        page_data = extract_data()
        if not page_data:
            break
        all_data.extend(page_data)
        
        try:
            next_button = driver.find_element(By.XPATH, '//li[@class="pagination-next"]/a')
            if 'disabled' in next_button.get_attribute('class'):
                break
            next_button.click()
            time.sleep(2)  # Esperar um pouco para a próxima página carregar
        except Exception as e:
            print(f"Erro ao navegar para a próxima página: {e}")
            break

    # Função para extrair dados de "Quantidade Teórica Total" e "Redutor"
    def extract_footer_data():
        try:
            footer = driver.find_element(By.TAG_NAME, 'tfoot')
            total_quantity = footer.find_element(By.XPATH, './/td[contains(text(), "Quantidade Teórica Total")]/following-sibling::td[1]').text
            total_part = footer.find_element(By.XPATH, './/td[contains(text(), "Quantidade Teórica Total")]/following-sibling::td[2]').text
            total_part_acum = footer.find_element(By.XPATH, './/td[contains(text(), "Quantidade Teórica Total")]/following-sibling::td[3]').text

            redutor = footer.find_element(By.XPATH, './/td[contains(text(), "Redutor")]/following-sibling::td').text

            return {
                'Quantidade Teórica Total': total_quantity,
                'Part (%) Total': total_part,
                'Part (%) Acum Total': total_part_acum,
                'Redutor': redutor
            }
        except Exception as e:
            print(f"Erro ao extrair dados de rodapé: {e}")
            return {}

    # Extrair os dados do rodapé após a última página ser carregada
    footer_data = extract_footer_data()

    # Verificar se os dados foram extraídos corretamente
    if not all_data:
        print("Nenhum dado foi extraído. Verifique os XPaths e a estrutura da tabela.")
    else:
        columns = ['Setor', 'Código', 'Ação', 'Tipo', 'Qtde. Teórica', 'Part. (%)', 'Part. (%)Acum.']
        df = pd.DataFrame(all_data, columns=columns)

        # Adicionar dados de rodapé ao DataFrame
        df_footer = pd.DataFrame([[
            'Quantidade Teórica Total',
            '',
            '',
            '',
            footer_data.get('Quantidade Teórica Total', ''),
            footer_data.get('Part (%) Total', ''),
            footer_data.get('Part (%) Acum Total', '')
        ], [
            'Redutor',
            '',
            '',
            '',
            footer_data.get('Redutor', ''),
            '',
            ''
        ]], columns=columns)
        
        df = pd.concat([df, df_footer], ignore_index=True)

        # Adicionar coluna com a data de extração
        today = datetime.today().strftime("%Y-%m-%d")
        df['dt_extract'] = pd.Series([str(today) for _ in range(len(df.index))]) 

        # Salvar os dados em um arquivo CSV (opcional)
        df.to_csv('carteira_do_dia_completa.csv', index=False)
        
        # Enviar os dados em parquet para o s3
        bucket_name = "bovespa-raw-bucket-mlops"
        file_name = f"carteira-do-dia-{today}"
        save_df_to_s3_parquet(df, bucket_name, file_name)

        print("Dados extraídos e salvos com sucesso:")
        print(df)
finally:
    # Fechar o WebDriver
    driver.quit()
