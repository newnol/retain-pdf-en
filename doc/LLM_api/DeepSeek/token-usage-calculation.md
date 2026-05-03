A token is the basic unit used by the model to represent natural language text, and it is also our billing unit. It can be intuitively understood as a "word" or "character." Generally, 1 Chinese word, 1 English word, 1 number, or 1 symbol counts as 1 token.

The approximate conversion ratio between tokens and character count in the model is as follows:

1 English character ≈ 0.3 tokens.
1 Chinese character ≈ 0.6 tokens.
However, since different models have different tokenization strategies, the conversion ratios may also vary. The actual number of tokens processed each time is subject to the model's response. You can check it in the usage field of the response.