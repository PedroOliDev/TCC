    document.getElementById("cep").addEventListener("blur", function() {
        let cep = this.value.replace(/\D/g, ""); // Remove caracteres não numéricos

        if (cep.length !== 8) {
            alert("CEP inválido! Digite um CEP com 8 números.");
            return;
        }

        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then(response => response.json())
            .then(data => {
                if (data.erro) {
                    alert("CEP não encontrado!");
                    return;
                }

                // Preenche os dados na tela
                document.getElementById("endereco").textContent = `Rua: ${data.logradouro || "-"}`;
                document.getElementById("bairro").textContent = `Bairro: ${data.bairro || "-"}`;
                document.getElementById("cidade").textContent = `Cidade: ${data.localidade || "-"}`;
                document.getElementById("estado").textContent = `Estado: ${data.uf || "-"}`;
            })

        });