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


        function validarTelefone() {
            
            const input = document.getElementById("numero").value;
      
            // Remove todos os caracteres que não são dígitos
            const numero = input.replace(/\D/g, "");
      
            const resultado = document.getElementById("resultado");
      
            if (/^\d{11}$/.test(numero)) {
              resultado.textContent = "✅ Número válido!";
              resultado.style.color = "green";
            } else {
              resultado.textContent = "❌ Número inválido. Digite no formato (11) 91234-5678 ou 11912345678.";
              resultado.style.color = "red";
            }
          }

          function validarEmail() {
            event.preventDefault(); // Impede o envio real do formulário
      
            const email = document.getElementById("email").value;
            const resultado = document.getElementById("resultado-email");
      
            // Regex simples para validação de e-mail
            const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      
            if (emailValido.test(email)) {
              resultado.textContent = "✅ E-mail válido!";
              resultado.style.color = "green";
            } else {
              resultado.textContent = "❌ E-mail inválido. Verifique o formato (exemplo@dominio.com).";
              resultado.style.color = "red";
            }
          };
          