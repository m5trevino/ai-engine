---
created: 2026-02-28T04:29:22 (UTC -08:00)
tags: []
source: https://ai.google.dev/gemini-api/docs/libraries
author: 
---

# Understand and count tokens  |  Gemini API  |  Google AI for Developers

> ## Excerpt
> Get started

---
[Skip to main content](https://ai.google.dev/gemini-api/docs/libraries#main-content)

-   [Gemini API](https://ai.google.dev/gemini-api/docs)
    -   [Docs](https://ai.google.dev/gemini-api/docs)
    -   [API reference](https://ai.google.dev/api)
-   [Get API key](https://aistudio.google.com/apikey)
-   [Cookbook](https://github.com/google-gemini/cookbook)
-   [Community](https://discuss.ai.google.dev/c/gemini-api/)

-   Get started
    
-   [Overview](https://ai.google.dev/gemini-api/docs)
-   [Quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
-   [API keys](https://ai.google.dev/gemini-api/docs/api-key)
-   [Libraries](https://ai.google.dev/gemini-api/docs/libraries)
-   [Pricing](https://ai.google.dev/gemini-api/docs/pricing)
-   [Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
-   Models
    
-   [All models](https://ai.google.dev/gemini-api/docs/models)
-   [Gemini 3](https://ai.google.dev/gemini-api/docs/gemini-3)
-   [Nano Banana](https://ai.google.dev/gemini-api/docs/image-generation)
-   [Veo](https://ai.google.dev/gemini-api/docs/video)
-   [Lyria](https://ai.google.dev/gemini-api/docs/music-generation)
-   [Imagen](https://ai.google.dev/gemini-api/docs/imagen)
-   [Text-to-speech](https://ai.google.dev/gemini-api/docs/speech-generation)
-   [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
-   [Robotics](https://ai.google.dev/gemini-api/docs/robotics-overview)
-   Core capabilities
    
-   [Text](https://ai.google.dev/gemini-api/docs/text-generation)

-   [Documents](https://ai.google.dev/gemini-api/docs/document-processing)

-   [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
-   [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
-   [Long context](https://ai.google.dev/gemini-api/docs/long-context)
-   Tools and agents
    
-   [Overview](https://ai.google.dev/gemini-api/docs/tools)
-   [Deep Research](https://ai.google.dev/gemini-api/docs/deep-research)
-   [Google Search](https://ai.google.dev/gemini-api/docs/google-search)
-   [Google Maps](https://ai.google.dev/gemini-api/docs/maps-grounding)
-   [Code execution](https://ai.google.dev/gemini-api/docs/code-execution)
-   [URL context](https://ai.google.dev/gemini-api/docs/url-context)
-   [Computer Use](https://ai.google.dev/gemini-api/docs/computer-use)
-   [File Search](https://ai.google.dev/gemini-api/docs/file-search)
-   Live API
    
-   [Get started](https://ai.google.dev/gemini-api/docs/live)
-   [Capabilities](https://ai.google.dev/gemini-api/docs/live-guide)
-   [Tool use](https://ai.google.dev/gemini-api/docs/live-tools)
-   [Session management](https://ai.google.dev/gemini-api/docs/live-session)
-   [Ephemeral tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)
-   Guides
    
-   [Coding agent skills](https://ai.google.dev/gemini-api/docs/coding-agents)
-   [Batch API](https://ai.google.dev/gemini-api/docs/batch-api)

-   [Context caching](https://ai.google.dev/gemini-api/docs/caching)
-   [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
-   [Media resolution](https://ai.google.dev/gemini-api/docs/media-resolution)
-   [Token counting](https://ai.google.dev/gemini-api/docs/tokens)
-   [Prompt engineering](https://ai.google.dev/gemini-api/docs/prompting-strategies)

-   Resources
    
-   [Release notes](https://ai.google.dev/gemini-api/docs/changelog)
-   [Deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
-   [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
-   [Billing info](https://ai.google.dev/gemini-api/docs/billing)
-   [Migrate to Gen AI SDK](https://ai.google.dev/gemini-api/docs/migrate)
-   [API troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)
-   [Partner and library integrations](https://ai.google.dev/gemini-api/docs/partner-integration)

-   Policies
    
-   [Terms of service](https://ai.google.dev/gemini-api/terms)
-   [Available regions](https://ai.google.dev/gemini-api/docs/available-regions)
-   [Abuse monitoring](https://ai.google.dev/gemini-api/docs/usage-policies)
-   [Feedback information](https://ai.google.dev/gemini-api/docs/feedback-policies)

-   On this page
-   [About tokens](https://ai.google.dev/gemini-api/docs/libraries#about-tokens)
-   [Count tokens](https://ai.google.dev/gemini-api/docs/libraries#count-tokens)
    -   [Count text tokens](https://ai.google.dev/gemini-api/docs/libraries#text-tokens)
    -   [Count multi-turn (chat) tokens](https://ai.google.dev/gemini-api/docs/libraries#multi-turn-tokens)
    -   [Count multimodal tokens](https://ai.google.dev/gemini-api/docs/libraries#multimodal-tokens)
-   [Context windows](https://ai.google.dev/gemini-api/docs/libraries#context-windows)

Gemini and other generative AI models process input and output at a granularity called a _token_.

**For Gemini models, a token is equivalent to about 4 characters. 100 tokens is equal to about 60-80 English words.**

## About tokens

Tokens can be single characters like `z` or whole words like `cat`. Long words are broken up into several tokens. The set of all tokens used by the model is called the vocabulary, and the process of splitting text into tokens is called _tokenization_.

When billing is enabled, the [cost of a call to the Gemini API](https://ai.google.dev/pricing) is determined in part by the number of input and output tokens, so knowing how to count tokens can be helpful.

You can try out counting tokens in our Colab.

## Count tokens

All input to and output from the Gemini API is tokenized, including text, image files, and other non-text modalities.

You can count tokens in the following ways:

-   **Call [`count_tokens`](https://ai.google.dev/api/rest/v1/models/countTokens) with the input of the request.**  
    This returns the total number of tokens in _the input only_. You can make this call before sending the input to the model to check the size of your requests.
    
-   **Use the `usage_metadata` attribute on the `response` object after calling `generate_content`.**  
    This returns the total number of tokens in _both the input and the output_: `total_token_count`.  
    It also returns the token counts of the input and output separately: `prompt_token_count` (input tokens) and `candidates_token_count` (output tokens).
    
    If you are using a [thinking model](https://ai.google.dev/gemini-api/docs/thinking), the token used during the thinking process are returned in `thoughts_token_count`. And if you are using [Context caching](https://ai.google.dev/gemini-api/docs/caching), the cached token count will be in `cached_content_token_count`.
    

### Count text tokens

If you call `count_tokens` with a text-only input, it returns the token count of the text in _the input only_ (`total_tokens`). You can make this call before calling `generate_content` to check the size of your requests.

Another option is calling `generate_content` and then using the `usage_metadata` attribute on the `response` object to get the following:

-   The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
-   The token count for the thinking process (`thoughts_token_count`)
-   The total number of tokens in _both the input and the output_ (`total_token_count`)
    

```
from google import genai

client = genai.Client()
prompt = "The quick brown fox jumps over the lazy dog."

total_tokens = client.models.count_tokens(
    model="gemini-3-flash-preview", contents=prompt
)
print("total_tokens: ", total_tokens)

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents=prompt
)

print(response.usage_metadata)
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});
const prompt = "The quick brown fox jumps over the lazy dog.";

async function main() {
  const countTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: prompt,
  });
  console.log(countTokensResponse.totalTokens);

  const generateResponse = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: prompt,
  });
  console.log(generateResponse.usageMetadata);
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)

// Convert prompt to a slice of *genai.Content using the helper.
contents := []*genai.Content{
  genai.NewContentFromText(prompt, genai.RoleUser),
}
countResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  return err
}
fmt.Println("total_tokens:", countResp.TotalTokens)

response, err := client.Models.GenerateContent(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
usageMetadata, err := json.MarshalIndent(response.UsageMetadata, "", "  ")
if err != nil {
  log.Fatal(err)
}
fmt.Println(string(usageMetadata))
    ```
```

### Count multi-turn (chat) tokens

If you call `count_tokens` with the chat history, it returns the total token count of the text from each role in the chat (`total_tokens`).

Another option is calling `send_message` and then using the `usage_metadata` attribute on the `response` object to get the following:

-   The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
-   The token count for the thinking process (`thoughts_token_count`)
-   The total number of tokens in _both the input and the output_ (`total_token_count`)

To understand how big your next conversational turn will be, you need to append it to the history when you call `count_tokens`.

```
from google import genai
from google.genai import types

client = genai.Client()

chat = client.chats.create(
    model="gemini-3-flash-preview",
    history=[
        types.Content(
            role="user", parts=[types.Part(text="Hi my name is Bob")]
        ),
        types.Content(role="model", parts=[types.Part(text="Hi Bob!")]),
    ],
)

print(
    client.models.count_tokens(
        model="gemini-3-flash-preview", contents=chat.get_history()
    )
)

response = chat.send_message(
    message="In one sentence, explain how a computer works to a young child."
)
print(response.usage_metadata)

extra = types.UserContent(
    parts=[
        types.Part(
            text="What is the meaning of life?",
        )
    ]
)
history = [*chat.get_history(), extra]
print(client.models.count_tokens(model="gemini-3-flash-preview", contents=history))
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});

async function main() {
  const history = [
    { role: "user", parts: [{ text: "Hi my name is Bob" }] },
    { role: "model", parts: [{ text: "Hi Bob!" }] },
  ];
  const chat = ai.chats.create({
    model: "gemini-3-flash-preview",
    history: history,
  });

  const countTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: chat.getHistory(),
  });
  console.log(countTokensResponse.totalTokens);

  const chatResponse = await chat.sendMessage({
    message: "In one sentence, explain how a computer works to a young child.",
  });
  console.log(chatResponse.usageMetadata);

  const extraMessage = {
    role: "user",
    parts: [{ text: "What is the meaning of life?" }],
  };
  const combinedHistory = [...chat.getHistory(), extraMessage];
  const combinedCountTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: combinedHistory,
  });
  console.log(
    "Combined history token count:",
    combinedCountTokensResponse.totalTokens,
  );
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)

history := []*genai.Content{
  {Role: genai.RoleUser, Parts: []*genai.Part({Text: "Hi my name is Bob"})},
  {Role: genai.RoleModel, Parts: []*genai.Part({Text: "Hi Bob!"})},
}
chat, err := client.Chats.Create(ctx, "gemini-3-flash-preview", nil, history)
if err != nil {
  log.Fatal(err)
}

firstTokenResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", chat.History(false), nil)
if err != nil {
  log.Fatal(err)
}
fmt.Println(firstTokenResp.TotalTokens)

resp, err := chat.SendMessage(ctx, genai.NewPartFromText("In one sentence, explain how a computer works to a young child."))
if err != nil {
  log.Fatal(err)
}
fmt.Printf("%#v\n", resp.UsageMetadata)

extra := genai.NewContentFromText("What is the meaning of life?", genai.RoleUser)
hist := chat.History(false)
hist = append(hist, extra)

secondTokenResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", hist, nil)
if err != nil {
  log.Fatal(err)
}
fmt.Println(secondTokenResp.TotalTokens)
```

### Count multimodal tokens

All input to the Gemini API is tokenized, including text, image files, and other non-text modalities. Note the following high-level key points about tokenization of multimodal input during processing by the Gemini API:

-   Image inputs with both dimensions <=384 pixels are counted as 258 tokens. Images larger in one or both dimensions are cropped and scaled as needed into tiles of 768x768 pixels, each counted as 258 tokens.
    
-   Video and audio files are converted to tokens at the following fixed rates: video at 263 tokens per second and audio at 32 tokens per second.
    

#### Media resolutions

[Gemini 3 models](https://ai.google.dev/gemini-api/docs/models#gemini-3) introduce granular control over multimodal vision processing with the `media_resolution` parameter. The `media_resolution` parameter determines the **maximum number of tokens allocated per input image or video frame.** Higher resolutions improve the model's ability to read fine text or identify small details, but increase token usage and latency.

For more details about the parameter and how it can impact token calculations, see the [media resolution](https://ai.google.dev/gemini-api/docs/media-resolution) guide.

#### Image files

If you call `count_tokens` with a text-and-image input, it returns the combined token count of the text and the image in _the input only_ (`total_tokens`). You can make this call before calling `generate_content` to check the size of your requests. You can also optionally call `count_tokens` on the text and the file separately.

Another option is calling `generate_content` and then using the `usage_metadata` attribute on the `response` object to get the following:

-   The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
-   The token count for the thinking process (`thoughts_token_count`)
-   The total number of tokens in _both the input and the output_ (`total_token_count`)

Example that uses an uploaded image from the File API:

```
from google import genai

client = genai.Client()
prompt = "Tell me about this image"
your_image_file = client.files.upload(file=media / "organ.jpg")

print(
    client.models.count_tokens(
        model="gemini-3-flash-preview", contents=[prompt, your_image_file]
    )
)

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents=[prompt, your_image_file]
)
print(response.usage_metadata)
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});
const prompt = "Tell me about this image";

async function main() {
  const organ = await ai.files.upload({
    file: path.join(media, "organ.jpg"),
    config: { mimeType: "image/jpeg" },
  });

  const countTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: createUserContent([
      prompt,
      createPartFromUri(organ.uri, organ.mimeType),
    ]),
  });
  console.log(countTokensResponse.totalTokens);

  const generateResponse = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: createUserContent([
      prompt,
      createPartFromUri(organ.uri, organ.mimeType),
    ]),
  });
  console.log(generateResponse.usageMetadata);
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)

file, err := client.Files.UploadFromPath(
  ctx, 
  filepath.Join(getMedia(), "organ.jpg"), 
  &genai.UploadFileConfig{
    MIMEType : "image/jpeg",
  },
)
if err != nil {
  log.Fatal(err)
}
parts := []*genai.Part{
  genai.NewPartFromText("Tell me about this image"),
  genai.NewPartFromURI(file.URI, file.MIMEType),
}
contents := []*genai.Content{
  genai.NewContentFromParts(parts, genai.RoleUser),
}

tokenResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
fmt.Println("Multimodal image token count:", tokenResp.TotalTokens)

response, err := client.Models.GenerateContent(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
usageMetadata, err := json.MarshalIndent(response.UsageMetadata, "", "  ")
if err != nil {
  log.Fatal(err)
}
fmt.Println(string(usageMetadata))
```

Example that provides the image as inline data:

```
from google import genai
import PIL.Image

client = genai.Client()
prompt = "Tell me about this image"
your_image_file = PIL.Image.open(media / "organ.jpg")

print(
    client.models.count_tokens(
        model="gemini-3-flash-preview", contents=[prompt, your_image_file]
    )
)

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents=[prompt, your_image_file]
)
print(response.usage_metadata)
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});
const prompt = "Tell me about this image";
const imageBuffer = fs.readFileSync(path.join(media, "organ.jpg"));

const imageBase64 = imageBuffer.toString("base64");

const contents = createUserContent([
  prompt,
  createPartFromBase64(imageBase64, "image/jpeg"),
]);

async function main() {
  const countTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: contents,
  });
  console.log(countTokensResponse.totalTokens);

  const generateResponse = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: contents,
  });
  console.log(generateResponse.usageMetadata);
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)

imageBytes, err := os.ReadFile("organ.jpg")
if err != nil {
    log.Fatalf("Failed to read image file: %v", err)
}
parts := []*genai.Part{
  genai.NewPartFromText("Tell me about this image"),
  {
        InlineData: &genai.Blob{
              MIMEType: "image/jpeg",
              Data:     imageBytes,
        },
  },
}
contents := []*genai.Content{
  genai.NewContentFromParts(parts, genai.RoleUser),
}

tokenResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
fmt.Println("Multimodal image token count:", tokenResp.TotalTokens)

response, err := client.Models.GenerateContent(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
usageMetadata, err := json.MarshalIndent(response.UsageMetadata, "", "  ")
if err != nil {
  log.Fatal(err)
}
fmt.Println(string(usageMetadata))
```

#### Video or audio files

Audio and video are each converted to tokens at the following fixed rates:

-   Video: 263 tokens per second
-   Audio: 32 tokens per second

If you call `count_tokens` with a text-and-video/audio input, it returns the combined token count of the text and the video/audio file in _the input only_ (`total_tokens`). You can make this call before calling `generate_content` to check the size of your requests. You can also optionally call `count_tokens` on the text and the file separately.

Another option is calling `generate_content` and then using the `usage_metadata` attribute on the `response` object to get the following:

-   The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
-   The token count for the thinking process (`thoughts_token_count`)
-   The total number of tokens in _both the input and the output_ (`total_token_count`).
    

```
from google import genai
import time

client = genai.Client()
prompt = "Tell me about this video"
your_file = client.files.upload(file=media / "Big_Buck_Bunny.mp4")

while not your_file.state or your_file.state.name != "ACTIVE":
    print("Processing video...")
    print("File state:", your_file.state)
    time.sleep(5)
    your_file = client.files.get(name=your_file.name)

print(
    client.models.count_tokens(
        model="gemini-3-flash-preview", contents=[prompt, your_file]
    )
)

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents=[prompt, your_file]
)
print(response.usage_metadata)
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});
const prompt = "Tell me about this video";

async function main() {
  let videoFile = await ai.files.upload({
    file: path.join(media, "Big_Buck_Bunny.mp4"),
    config: { mimeType: "video/mp4" },
  });

  while (!videoFile.state || videoFile.state.toString() !== "ACTIVE") {
    console.log("Processing video...");
    console.log("File state: ", videoFile.state);
    await sleep(5000);
    videoFile = await ai.files.get({ name: videoFile.name });
  }

  const countTokensResponse = await ai.models.countTokens({
    model: "gemini-3-flash-preview",
    contents: createUserContent([
      prompt,
      createPartFromUri(videoFile.uri, videoFile.mimeType),
    ]),
  });
  console.log(countTokensResponse.totalTokens);

  const generateResponse = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: createUserContent([
      prompt,
      createPartFromUri(videoFile.uri, videoFile.mimeType),
    ]),
  });
  console.log(generateResponse.usageMetadata);
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)

file, err := client.Files.UploadFromPath(
  ctx,
  filepath.Join(getMedia(), "Big_Buck_Bunny.mp4"),
  &genai.UploadFileConfig{
    MIMEType : "video/mp4",
  },
)
if err != nil {
  log.Fatal(err)
}

for file.State == genai.FileStateUnspecified || file.State != genai.FileStateActive {
  fmt.Println("Processing video...")
  fmt.Println("File state:", file.State)
  time.Sleep(5 * time.Second)

  file, err = client.Files.Get(ctx, file.Name, nil)
  if err != nil {
    log.Fatal(err)
  }
}

parts := []*genai.Part{
  genai.NewPartFromText("Tell me about this video"),
  genai.NewPartFromURI(file.URI, file.MIMEType),
}
contents := []*genai.Content{
  genai.NewContentFromParts(parts, genai.RoleUser),
}

tokenResp, err := client.Models.CountTokens(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
fmt.Println("Multimodal video/audio token count:", tokenResp.TotalTokens)
response, err := client.Models.GenerateContent(ctx, "gemini-3-flash-preview", contents, nil)
if err != nil {
  log.Fatal(err)
}
usageMetadata, err := json.MarshalIndent(response.UsageMetadata, "", "  ")
if err != nil {
  log.Fatal(err)
}
fmt.Println(string(usageMetadata))
```

## Context windows

The models available through the Gemini API have context windows that are measured in tokens. The context window defines how much input you can provide and how much output the model can generate. You can determine the size of the context window by calling the [`models.get` endpoint](https://ai.google.dev/api/rest/v1/models/get) or by looking in the [models documentation](https://ai.google.dev/gemini-api/docs/models).

```
from google import genai

client = genai.Client()
model_info = client.models.get(model="gemini-3-flash-preview")
print(f"{model_info.input_token_limit=}")
print(f"{model_info.output_token_limit=}")
```

```
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({});

async function main() {
  const modelInfo = await ai.models.get({model: 'gemini-3-flash-preview'});
  console.log(modelInfo.inputTokenLimit);
  console.log(modelInfo.outputTokenLimit);
}

await main();
```

```
ctx := context.Background()
client, err := genai.NewClient(ctx, nil)
if err != nil {
  log.Fatal(err)
}
modelInfo, err := client.ModelInfo(ctx, "models/gemini-3-flash-preview")
if err != nil {
  log.Fatal(err)
}
fmt.Println("input token limit:", modelInfo.InputTokenLimit)
fmt.Println("output token limit:", modelInfo.OutputTokenLimit)
```

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2026-02-26 UTC.

The new page has loaded..
