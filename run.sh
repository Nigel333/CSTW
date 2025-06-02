#!/usr/bin/env bash

DIR=exp/chain/tdnn1_sp
DIR2=exp/chain/tdnn1_sp_online

name=$1
fakepath=$2
path=${fakepath:0:-5}.wav
kaldi=/mnt/KINGSTON/Kaldi/kaldi/egs/phoneTest
cstw=/mnt/KINGSTON/CSTW/CSTW

echo $name
echo $path
echo $fakepath

{
ffmpeg -y -i $fakepath -ar 48000 -ac 1 $path
sox $path ${path:0:-4}_sil.wav pad 1 1
mv ${path:0:-4}_sil.wav $path
duration=$(soxi -D $path)
rm $fakepath
python prep.py $(basename "$path" .wav) ${path%/*}/ $duration
cd $kaldi
utils/fix_data_dir.sh $cstw/${path%/*}
utils/validate_data_dir.sh $cstw/${path%/*}
cd $cstw
python finalize.py ${path%/*}/text /mnt/KINGSTON/Kaldi/kaldi/egs/phoneTest/data/local/dict/referenceW2Syll.txt ${path%/*}/text2
mv ${path%/*}/text2 ${path%/*}/text
}


cd $kaldi
utils/data/perturb_data_dir_speed_3way.sh --always-include-prefix true $cstw/${path%/*} $cstw/${path%/*}/aug
utils/fix_data_dir.sh $cstw/${path%/*}/aug
utils/validate_data_dir.sh $cstw/${path%/*}/aug

mfccdir=$cstw/${path%/*}/mfcc
steps/make_mfcc.sh --cmd run.pl --nj 3 --mfcc-config conf/mfcc_hires.conf $cstw/${path%/*}/aug $cstw/${path%/*}/make_hires $mfccdir;
steps/compute_cmvn_stats.sh $cstw/${path%/*}/aug $cstw/${path%/*}/make_hires $mfccdir;
utils/fix_data_dir.sh $cstw/${path%/*}/aug

steps/online/nnet2/extract_ivectors_online.sh --cmd run.pl --nj 3 $cstw/${path%/*}/aug exp/nnet3/extractor $cstw/${path%/*}/nnet3/ivectors_demoaug || exit 1;
steps/nnet3/decode.sh --acwt 1.0 --post-decode-acwt 10.0 --nj 3 --cmd run.pl --online-ivector-dir $cstw/${path%/*}/nnet3/ivectors_demoaug $DIR/graph_sw1_tg $cstw/${path%/*}/aug $DIR/${name}_$(basename "$path" .wav)_decode || exit 1;

steps/online/nnet3/prepare_online_decoding.sh --mfcc-config conf/mfcc_hires.conf data/ones exp/nnet3/extractor $DIR $DIR2
steps/online/nnet3/decode.sh --nj 3 --cmd run.pl --acwt 1.0 --post-decode-acwt 10.0 $DIR/graph_sw1_tg $cstw/${path%/*}/aug $DIR2/${name}_$(basename "$path" .wav)_decode || exit 1;

steps/get_ctm.sh --use-segments true --frame_shift 0.019 $cstw/${path%/*}/aug data/lang_test $DIR/${name}_$(basename "$path" .wav)_decode
steps/get_ctm.sh --use-segments true --frame_shift 0.019 $cstw/${path%/*}/aug data/lang_test $DIR2/${name}_$(basename "$path" .wav)_decode

rm -rf $cstw/${path%/*}/decode $cstw/${path%/*}/decode_online

cd $DIR/${name}_$(basename "$path" .wav)_decode
# Set your target destination for the best score_X folder
DESTINATION="$cstw/${path%/*}/decode/"
mkdir $DESTINATION
best_file=""
best_ser=1000
best_wer=1000
best_num=""

# Loop through all wer_*_*.txt files
for file in wer_*_*; do
  
    [[ -f "$file" ]] || continue  # skip if no match

    # Extract SER and WER from the file
    ser=$(grep "%SER" "$file" | awk '{print $2}')
    wer=$(grep "%WER" "$file" | awk '{print $2}')

    # Remove percent signs
    ser=${ser%\%}
    wer=${wer%\%}

    # Compare SER and WER
    if (( $(echo "$ser < $best_ser" | bc -l) )) || 
       { [[ "$ser" == "$best_ser" ]] && (( $(echo "$wer < $best_wer" | bc -l) )); }; then
        best_ser=$ser
        best_wer=$wer
        best_file="$file"
    fi
done

# Extract the first number (X) from filename wer_X_Y.Z.txt
if [[ "$best_file" =~ wer_([0-9]+)_[0-9.]+$ ]]; then
    best_num="${BASH_REMATCH[1]}"
    echo "Best file: $best_file (SER: $best_ser, WER: $best_wer)"
    echo "Moving score_$best_num to $DESTINATION"

    # Move the folder
    mv "score_$best_num/aug.ctm" "$DESTINATION"
    mv "$best_file" "$DESTINATION"
    filename="${best_file:4}"
    filename="${filename//_/.}"
    mv "scoring/${filename}.txt" "$DESTINATION/best.txt"

else
    echo "No matching best file found."
    exit 1
fi

cd ../../tdnn1_sp_online/${name}_$(basename "$path" .wav)_decode
DESTINATION="$cstw/${path%/*}/decode_online/"
mkdir $DESTINATION
best_file=""
best_ser=1000
best_wer=1000
best_num=""

# Loop through all wer_*_*.txt files
for file in wer_*_*; do
    [[ -f "$file" ]] || continue  # skip if no match

    # Extract SER and WER from the file
    ser=$(grep "%SER" "$file" | awk '{print $2}')
    wer=$(grep "%WER" "$file" | awk '{print $2}')

    # Remove percent signs
    ser=${ser%\%}
    wer=${wer%\%}

    # Compare SER and WER
    if (( $(echo "$ser < $best_ser" | bc -l) )) || 
       { [[ "$ser" == "$best_ser" ]] && (( $(echo "$wer < $best_wer" | bc -l) )); }; then
        best_ser=$ser
        best_wer=$wer
        best_file="$file"
    fi
done

# Extract the first number (X) from filename wer_X_Y.Z.txt
if [[ "$best_file" =~ wer_([0-9]+)_[0-9.]+$ ]]; then
    best_num="${BASH_REMATCH[1]}"
    echo "Best file: $best_file (SER: $best_ser, WER: $best_wer)"
    echo "Moving score_$best_num to $DESTINATION"

    # Move the folder
    mv "score_$best_num/aug.ctm" "$DESTINATION"
    mv "$best_file" "$DESTINATION"
    filename="${best_file:4}"
    filename="${filename//_/.}"
    mv "scoring/${filename}.txt" "$DESTINATION/best.txt"

else
    echo "No matching best file found."
    exit 1
fi

cd $kaldi
utils/syllable-processor.py $cstw/${path%/*}/decode/aug.ctm data/local/dict/referenceW2Syll.txt
utils/syllable-processor.py $cstw/${path%/*}/decode_online/aug.ctm data/local/dict/referenceW2Syll.txt
utils/syllable-filter-final.py $cstw/${path%/*}/decode/Output.txt
utils/syllable-filter-final.py $cstw/${path%/*}/decode_online/Output.txt

# RESULTS MAPPING

OUTPUT_FILE=$cstw/${path%/*}/decode/best.txt
INPUT_FILE=$cstw/${path%/*}/text
RESULT_FILE=$cstw/results/${name}_$(basename "$path" .wav | sed -E 's/[0-9]+[mf]$//').txt

# Read input line and extract syllables (all tokens, including ID if any)
read -r input_line < "$INPUT_FILE"
input_syllables=($(echo "$input_line" | cut -d' ' -f2-))
input_len=${#input_syllables[@]}
echo ${input_syllables[*]}

> "$RESULT_FILE"  # Clear the result file
best_score=-1
best_result=""
# Loop through each line in the output file

while IFS= read -r output_line; do
  output_syllables=($(echo "$output_line" | cut -d' ' -f2-))
  echo "DEBUG: ${output_syllables[*]}" >&2
  output_len=${#output_syllables[@]}
  echo "OUTPUTLEN: ${output_len}"
  # Adjust output syllables to match input length
  adjusted_output=()
  i=0
  j=0
  rep=0
  score=0
  current_result=""
	while [ "$output_len" -lt "$input_len" ]; do
		((output_len++))
	done
	echo "outputlen right now is ${output_len}"
  	while [ "$i" -lt "$input_len" ] && [ "$j" -lt "$output_len" ]; do
	    	if [ "${input_syllables[$i]}" == "${output_syllables[$j]}" ]; then
			((score++))
			current_result+="1"
			echo "current result is ${current_result}"
			((i++))
			((j++))
		elif [ "$output_len" -gt "$((input_len+rep))" ]; then
			((j++))
			((rep++))
			echo "Error, mismatched syllables, ${i} ${rep}"
		else
			current_result+="2"
			echo "current result is ${current_result}"
			((i++))
			((j++))
		fi
	done
		

 if [ "$score" -gt "$best_score" ]; then
    best_score=$score
    best_result=$current_result
 fi

done < "$OUTPUT_FILE"

echo "$best_result" >> "$RESULT_FILE"

echo "✅ Comparison complete. Results saved to $RESULT_FILE"


USERRELFILE=$cstw/${path%/*}/decode/RelativeLengths.txt
ORIGRELFILE=$cstw/RelativeLengths.txt
filename=$(basename "$path" .wav)
words=($(echo "${filename%%[0-9]*[mf]}" | tr '_' ' '))

echo ${words[@]}

diffs=()
for word in ${words[@]}; do
	nums=(); found=0; while IFS= read -r line; do
	  # Step 1: Look for the keyword line
	  if [[ $found -eq 0 && "$line" == *"$word"* ]]; then
	    found=1
	    continue  # skip the keyword line
	  fi

	  # Step 2: If found, parse the next non-blank lines until a blank or another keyword block starts
	  if [[ $found -eq 1 ]]; then
	    [[ -z "$line" ]] && break  # stop at blank line

	    # extract first number (float or int)
	    num=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+|[0-9]+' | head -n1)
	    if [[ -n "$num" ]]; then
	      nums+=("$num")
	    fi
	  fi
	done < $USERRELFILE
	
	if [[ "${words[0]}" == "Wala" && "${#words[@]}" -eq 1 ]]; then
	  word="WalaLeft"
	elif [[ "${words[0]}" == "Wala" && "${#words[@]}" -eq 2 ]]; then
	  word="WalaZero"
	fi
	
	numsref=(); found=0; while IFS= read -r line; do
	  if [[ $found -eq 0 && "$line" == *"$word"* ]]; then
	    found=1
	    continue  # skip the keyword line
	  fi

	  # Step 2: If found, parse the next non-blank lines until a blank or another keyword block starts
	  if [[ $found -eq 1 ]]; then
	    [[ -z "$line" ]] && break  # stop at blank line

	    # extract first number (float or int)
	    num=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+|[0-9]+' | head -n1)
	    if [[ -n "$num" ]]; then
	      numsref+=("$num")
	    fi
	  fi
	done < $ORIGRELFILE
	
	echo "${nums[@]}"
	echo "${numsref[@]}"
	
	for i in "${!nums[@]}"; do diffs+=($(awk -v x="${nums[i]}" -v y="${numsref[i]}" 'BEGIN { printf "%.4f", x - y }')); done

done
echo ${diffs[@]}
threshold=0.15
for ((i=0; i<${#best_result}; i++)); do
  digit="${best_result:$i:1}"
  diff=$(awk -v d="${diffs[i]}" 'BEGIN { print (d < 0 ? -d : d) }')
  
  # condition: change digit to 3 if diff >= threshold
  if (( $(awk -v d="$diff" -v t="$threshold" 'BEGIN { print (d >= t) ? 1 : 0 }') )) && [ $digit = "1" ]; then
    new_result+="3"
  else
    new_result+="$digit"
  fi
done

echo "$new_result" > "$RESULT_FILE"
